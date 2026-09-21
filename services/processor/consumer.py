from __future__ import annotations

import json
import logging
import sys
import time
from collections import defaultdict, deque
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from prometheus_client import Counter, Histogram, start_http_server

from common import config
from common.features import compute_features
from common.kafka_utils import create_consumer, create_producer, produce_json
from common.rules import classify_window
from common.schemas import ClassificationResult, Measurement
from services.processor.model import RandomForestModel

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s [processor] %(message)s")
logger = logging.getLogger(__name__)

METRICS_PORT = 8001

MESSAGES_CONSUMED = Counter("processor_messages_consumed_total", "Liczba skonsumowanych pomiarów surowych")
CLASSIFICATIONS = Counter(
    "processor_classifications_total", "Liczba klasyfikacji okien pomiarowych", ["label", "source"]
)
AGREEMENT = Counter(
    "processor_rule_rf_agreement_total",
    "Zgodność między etykietą z metodyki (rules) a predykcją Random Forest",
    ["match"],
)
PROCESSING_LATENCY = Histogram(
    "processor_processing_latency_seconds", "Czas przetworzenia jednego pomiaru (okno + klasyfikacja)"
)


class StationWindows:
    def __init__(self, window_size: int):
        self.window_size = window_size
        self._windows: dict[str, deque] = defaultdict(lambda: deque(maxlen=window_size))

    def add(self, measurement: Measurement) -> list[Measurement]:
        window = self._windows[measurement.station_id]
        window.append(measurement)
        return list(window)


def process_message(payload: dict, windows: StationWindows, model: RandomForestModel, producer) -> ClassificationResult:
    measurement = Measurement.from_dict(payload)
    window = windows.add(measurement)
    features = compute_features(window)

    rule_label, reasons = classify_window(features)

    model_label, confidence = model.predict(features)
    source = "random_forest"
    if model_label is None:
        model_label, confidence, source = rule_label, 1.0, "rules_fallback"

    agreement = model_label == rule_label

    result = ClassificationResult(
        station_id=features.station_id,
        station_name=features.station_name,
        window_start=features.window_start,
        window_end=features.window_end,
        features=features.to_dict(),
        rule_label=rule_label,
        rule_reasons=reasons,
        model_label=model_label,
        model_confidence=confidence,
        agreement=agreement,
    )

    produce_json(producer, config.TOPIC_CLASSIFIED, key=features.station_id, payload=result.to_dict())

    CLASSIFICATIONS.labels(label=model_label, source=source).inc()
    AGREEMENT.labels(match=str(agreement).lower()).inc()

    return result


def main() -> None:
    start_http_server(METRICS_PORT)
    logger.info("Metryki Prometheus na porcie %d", METRICS_PORT)

    consumer = create_consumer(group_id="air-quality-processor", topics=[config.TOPIC_RAW_MEASUREMENTS])
    producer = create_producer()
    model = RandomForestModel()
    windows = StationWindows(config.WINDOW_SIZE)

    logger.info("Processor uruchomiony. Rozmiar okna: %d, min. próbek: %d",
                config.WINDOW_SIZE, config.MIN_SAMPLES_IN_WINDOW)

    try:
        while True:
            msg = consumer.poll(timeout=1.0)
            if msg is None:
                continue
            if msg.error():
                logger.warning("Błąd konsumenta Kafka: %s", msg.error())
                continue

            start = time.perf_counter()
            try:
                payload = json.loads(msg.value().decode("utf-8"))
                result = process_message(payload, windows, model, producer)
                logger.info(
                    "%s: reguła=%s model=%s (%.2f) zgodność=%s",
                    result.station_id, result.rule_label, result.model_label,
                    result.model_confidence, result.agreement,
                )
            except Exception:
                logger.exception("Błąd przetwarzania wiadomości")
            finally:
                MESSAGES_CONSUMED.inc()
                PROCESSING_LATENCY.observe(time.perf_counter() - start)
                producer.poll(0)
    except KeyboardInterrupt:
        pass
    finally:
        consumer.close()
        producer.flush(5)


if __name__ == "__main__":
    main()
