from __future__ import annotations

import json
import logging
import threading
import time
from datetime import datetime, timedelta, timezone

from common import config
from common.kafka_utils import create_consumer
from common.schemas import ClassificationResult
from services.api import store
from services.api.metrics import (
    EXPLANATION_LATENCY,
    EXPLANATION_QUEUE_DEPTH,
    EXPLANATIONS_TOTAL,
    RAG_RETRIEVAL_LATENCY,
)
from services.api.rag.explainer import generate_explanation
from services.api.rag.retriever import retrieve_context

logger = logging.getLogger(__name__)

BACKLOG_WINDOW_SECONDS = 300
IDLE_POLL_SECONDS = 2.0


def _result_from_row(row: dict) -> ClassificationResult:
    return ClassificationResult(
        station_id=row["station_id"],
        station_name=row["station_name"],
        window_start=row["window_start"],
        window_end=row["window_end"],
        features=row["features"],
        rule_label=row["rule_label"],
        rule_reasons=row["rule_reasons"],
        model_label=row["model_label"],
        model_confidence=row["model_confidence"],
        agreement=row["agreement"],
        classified_at=row["classified_at"],
    )


def _ingest_and_fallback_loop(stop_event: threading.Event) -> None:
    consumer = create_consumer(group_id="air-quality-api-explainer", topics=[config.TOPIC_CLASSIFIED])
    logger.info("Wątek zapisu klasyfikacji (RAG + szablon) uruchomiony, temat: %s", config.TOPIC_CLASSIFIED)
    try:
        while not stop_event.is_set():
            msg = consumer.poll(timeout=1.0)
            if msg is None:
                continue
            if msg.error():
                logger.warning("Błąd konsumenta Kafka: %s", msg.error())
                continue
            try:
                payload = json.loads(msg.value().decode("utf-8"))
                result = ClassificationResult.from_dict(payload)

                t0 = time.perf_counter()
                context_chunks = retrieve_context(result)
                RAG_RETRIEVAL_LATENCY.observe(time.perf_counter() - t0)

                explanation, source = generate_explanation(result, context_chunks, force_fallback=True)
                store.insert_classification(result, explanation, source)
                EXPLANATIONS_TOTAL.labels(source=source).inc()
            except Exception:
                logger.exception("Błąd zapisu klasyfikacji")
    finally:
        consumer.close()


def _llm_enrichment_loop(stop_event: threading.Event) -> None:
    logger.info("Wątek wzbogacania wyjaśnień LLM uruchomiony (niezależny od zapisu klasyfikacji).")
    last_station_id: str | None = None
    while not stop_event.is_set():
        try:
            candidate = store.get_next_enrichment_candidate(last_station_id)
            cutoff = (datetime.now(timezone.utc) - timedelta(seconds=BACKLOG_WINDOW_SECONDS)).isoformat()
            EXPLANATION_QUEUE_DEPTH.set(store.count_fallback_since(cutoff))

            if candidate is None:
                stop_event.wait(IDLE_POLL_SECONDS)
                continue

            last_station_id = candidate["station_id"]
            result = _result_from_row(candidate)
            t0 = time.perf_counter()
            context_chunks = retrieve_context(result)
            RAG_RETRIEVAL_LATENCY.observe(time.perf_counter() - t0)

            t1 = time.perf_counter()
            explanation, source = generate_explanation(result, context_chunks)
            EXPLANATION_LATENCY.observe(time.perf_counter() - t1)

            if source == "llm":
                store.update_explanation(candidate["id"], explanation, source)
                EXPLANATIONS_TOTAL.labels(source="llm").inc()
        except Exception:
            logger.exception("Błąd wątku wzbogacania wyjaśnień LLM")
            stop_event.wait(5.0)


def start_background_consumer() -> threading.Event:
    stop_event = threading.Event()

    threading.Thread(
        target=_ingest_and_fallback_loop, args=(stop_event,), daemon=True, name="classified-ingest"
    ).start()
    threading.Thread(
        target=_llm_enrichment_loop, args=(stop_event,), daemon=True, name="llm-enrichment"
    ).start()

    return stop_event
