from __future__ import annotations

import logging
from typing import Optional

import requests

logger = logging.getLogger(__name__)

BASE_URL = "https://api.gios.gov.pl/pjp-api/rest"
REQUEST_TIMEOUT = 10

PARAM_MAP = {
    "PM10": "pm10",
    "PM2.5": "pm25",
    "NO2": "no2",
    "O3": "o3",
    "SO2": "so2",
    "CO": "co",
}


def get_station_sensors(station_id: str) -> list[dict]:
    try:
        resp = requests.get(f"{BASE_URL}/station/sensors/{station_id}", timeout=REQUEST_TIMEOUT)
        resp.raise_for_status()
        return resp.json()
    except requests.RequestException as exc:
        logger.warning("Nie udało się pobrać sensorów stacji %s: %s", station_id, exc)
        return []


def get_latest_sensor_value(sensor_id: int) -> Optional[float]:
    try:
        resp = requests.get(f"{BASE_URL}/data/getData/{sensor_id}", timeout=REQUEST_TIMEOUT)
        resp.raise_for_status()
        data = resp.json()
        for point in data.get("values", []):
            if point.get("value") is not None:
                return float(point["value"])
        return None
    except (requests.RequestException, ValueError, KeyError) as exc:
        logger.warning("Nie udało się pobrać danych sensora %s: %s", sensor_id, exc)
        return None


def fetch_station_measurement(station_id: str, station_name: str) -> dict:
    from datetime import datetime, timezone

    values: dict[str, Optional[float]] = {v: None for v in PARAM_MAP.values()}
    for sensor in get_station_sensors(station_id):
        formula = sensor.get("param", {}).get("paramFormula")
        field = PARAM_MAP.get(formula)
        if field is None:
            continue
        values[field] = get_latest_sensor_value(sensor["id"])

    return {
        "station_id": str(station_id),
        "station_name": station_name,
        "timestamp": datetime.now(timezone.utc).isoformat(),
        **values,
    }


def find_stations(name_query: Optional[str] = None, limit: int = 5) -> list[dict]:
    try:
        resp = requests.get(f"{BASE_URL}/station/findAll", timeout=REQUEST_TIMEOUT)
        resp.raise_for_status()
        stations = resp.json()
    except requests.RequestException as exc:
        logger.warning("Nie udało się pobrać listy stacji GIOŚ: %s", exc)
        return []

    if name_query:
        stations = [s for s in stations if name_query.lower() in s.get("stationName", "").lower()]
    return stations[:limit]


if __name__ == "__main__":
    import json as _json

    print("Przykładowe stacje zawierające 'Warszawa':")
    print(_json.dumps(find_stations("Warszawa"), indent=2, ensure_ascii=False))
