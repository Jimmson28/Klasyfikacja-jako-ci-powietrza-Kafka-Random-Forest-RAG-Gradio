from __future__ import annotations

import logging
import sys
from contextlib import asynccontextmanager
from datetime import datetime, timedelta, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from prometheus_client import make_asgi_app

from common import config
from common.features import compute_features
from common.rules import classify_window
from common.schemas import ClassificationResult, Measurement
from services.api import store
from services.api.consumer_thread import start_background_consumer
from services.api.metrics import EXPLANATIONS_TOTAL, MANUAL_CLASSIFY_TOTAL
from services.api.rag.explainer import generate_explanation
from services.api.rag.ingest_kb import ensure_ingested
from services.api.rag.retriever import retrieve_context
from services.api.schemas import ManualClassifyRequest

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s [api] %(message)s")
logger = logging.getLogger(__name__)

_stop_event = None


@asynccontextmanager
async def lifespan(app: FastAPI):
    store.init_db()
    try:
        ensure_ingested()
    except Exception:
        logger.exception("Nie udało się zaindeksować bazy wiedzy RAG w Milvus - endpointy będą działać bez kontekstu RAG.")

    global _stop_event
    _stop_event = start_background_consumer()
    logger.info("API wystartowało.")
    yield
    if _stop_event:
        _stop_event.set()


app = FastAPI(
    title="Air Quality Classifier API",
    description="Klasyfikacja i semantyczne objaśnianie stanu jakości powietrza (Kafka + Random Forest + RAG/LLM).",
    version="0.1.0",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware, allow_origins=["*"], allow_methods=["*"], allow_headers=["*"],
)
app.mount("/metrics", make_asgi_app())


@app.get("/health")
def health():
    return {"status": "ok"}


@app.get("/classes")
def list_classes():
    return [
        {"id": label, "name": config.LABEL_DISPLAY_NAMES[label]}
        for label in config.ALL_LABELS
    ]


@app.get("/stations")
def list_stations():
    return store.list_known_stations()


@app.get("/overview")
def overview():
    return store.get_latest_overview()


@app.get("/stations/{station_id}/latest")
def station_latest(station_id: str):
    result = store.get_latest_for_station(station_id)
    if result is None:
        raise HTTPException(status_code=404, detail=f"Brak danych dla stacji '{station_id}'")
    return result


@app.get("/stations/{station_id}/history")
def station_history(station_id: str, limit: int = 50):
    return store.get_history_for_station(station_id, limit=min(limit, 500))


@app.post("/classify")
def manual_classify(req: ManualClassifyRequest):
    MANUAL_CLASSIFY_TOTAL.inc()

    base_time = datetime.now(timezone.utc) - timedelta(minutes=5 * len(req.measurements))
    measurements = [
        Measurement(
            station_id=req.station_id,
            station_name=req.station_name,
            timestamp=(base_time + timedelta(minutes=5 * i)).isoformat(),
            **m.model_dump(),
        )
        for i, m in enumerate(req.measurements)
    ]

    features = compute_features(measurements)
    label, reasons = classify_window(features)

    result = ClassificationResult(
        station_id=features.station_id,
        station_name=features.station_name,
        window_start=features.window_start,
        window_end=features.window_end,
        features=features.to_dict(),
        rule_label=label,
        rule_reasons=reasons,
        model_label=label,
        model_confidence=1.0,
        agreement=True,
    )

    context_chunks = retrieve_context(result)
    explanation, source = generate_explanation(result, context_chunks)
    EXPLANATIONS_TOTAL.labels(source=source).inc()

    store.insert_classification(result, explanation, source)

    return {
        **result.to_dict(),
        "explanation": explanation,
        "explanation_source": source,
        "context_chunks": context_chunks,
    }
