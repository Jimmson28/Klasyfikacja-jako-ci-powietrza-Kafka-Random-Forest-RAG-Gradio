from __future__ import annotations

import logging
import os
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from prometheus_client import Counter, start_http_server

from common import config
from common.kafka_utils import create_producer, produce_json
from common.schemas import Measurement
from common.simulator import LiveStationSimulator

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s [producer] %(message)s")
logger = logging.getLogger(__name__)

DATA_SOURCE = os.environ.get("DATA_SOURCE", "simulate")
INTERVAL_SECONDS = float(os.environ.get("PRODUCE_INTERVAL_SECONDS", "5"))
METRICS_PORT = int(os.environ.get("PRODUCER_METRICS_PORT", "8002"))

DEFAULT_STATIONS = [
    ("sim-warszawa-mokotow", "Warszawa - Mokotów (symulacja)"),
    ("sim-krakow-krasinskiego", "Kraków - Krasińskiego (symulacja)"),
    ("sim-wroclaw-korzeniowskiego", "Wrocław - Korzeniowskiego (symulacja)"),
    ("sim-poznan-rataje", "Poznań - Rataje (symulacja)"),
    ("sim-gdansk-wrzeszcz", "Gdańsk - Wrzeszcz (symulacja)"),
    ("sim-lodz-widzew", "Łódź - Widzew (symulacja)"),
    ("sim-katowice-srodmiescie", "Katowice - Śródmieście (symulacja)"),
    ("sim-szczecin-pogodno", "Szczecin - Pogodno (symulacja)"),
]

MESSAGES_PRODUCED = Counter(
    "producer_messages_total", "Liczba pomiarów opublikowanych na Kafkę", ["station_id", "source"]
)
PRODUCE_ERRORS = Counter(
    "producer_errors_total", "Liczba błędów podczas pobierania/publikacji pomiarów", ["source"]
)


def parse_stations() -> list[tuple[str, str]]:
    raw = os.environ.get("STATIONS")
    if not raw:
        return DEFAULT_STATIONS
    stations = []
    for part in raw.split(";"):
        station_id, _, name = part.partition(":")
        stations.append((station_id.strip(), (name or station_id).strip()))
    return stations


def run_simulate(producer, stations: list[tuple[str, str]]) -> None:
    simulators = {
        station_id: LiveStationSimulator(station_id, name, seed=hash(station_id) % (2**31))
        for station_id, name in stations
    }
    logger.info("Tryb symulacji, stacje: %s", [s[0] for s in stations])
    while True:
        for station_id, sim in simulators.items():
            measurement = sim.next_measurement()
            produce_json(producer, config.TOPIC_RAW_MEASUREMENTS, key=station_id, payload=measurement.to_dict())
            MESSAGES_PRODUCED.labels(station_id=station_id, source="simulate").inc()
        producer.flush(0)
        time.sleep(INTERVAL_SECONDS)


def run_gios(producer, stations: list[tuple[str, str]]) -> None:
    from services.producer import gios_client

    logger.info("Tryb GIOŚ (dane rzeczywiste), stacje: %s", [s[0] for s in stations])
    while True:
        for station_id, name in stations:
            try:
                payload = gios_client.fetch_station_measurement(station_id, name)
                measurement = Measurement.from_dict(payload)
                produce_json(
                    producer, config.TOPIC_RAW_MEASUREMENTS, key=station_id, payload=measurement.to_dict()
                )
                MESSAGES_PRODUCED.labels(station_id=station_id, source="gios").inc()
            except Exception:
                logger.exception("Błąd pobierania danych GIOŚ dla stacji %s", station_id)
                PRODUCE_ERRORS.labels(source="gios").inc()
        producer.flush(0)
        time.sleep(INTERVAL_SECONDS)


def main() -> None:
    start_http_server(METRICS_PORT)
    logger.info("Metryki Prometheus na porcie %d", METRICS_PORT)

    producer = create_producer()
    stations = parse_stations()

    if DATA_SOURCE == "gios":
        run_gios(producer, stations)
    else:
        run_simulate(producer, stations)


if __name__ == "__main__":
    main()
