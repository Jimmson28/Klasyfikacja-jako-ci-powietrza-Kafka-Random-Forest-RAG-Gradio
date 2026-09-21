from __future__ import annotations

import random
from datetime import datetime, timedelta, timezone
from enum import Enum
from typing import Optional

from common.schemas import Measurement

STEP_MINUTES_DEFAULT = 5


class ScenarioIntent(str, Enum):
    TYPICAL = "typical"
    ELEVATED = "elevated"
    RAPID_WORSENING = "rapid_worsening"
    IMPROVEMENT = "improvement"
    UNSTABLE = "unstable"
    INSUFFICIENT_DATA = "insufficient_data"


def _clip_positive(v: float) -> float:
    return max(0.0, v)


def _build_measurements(
    values: dict[str, list[Optional[float]]],
    station_id: str,
    station_name: str,
    start_time: Optional[datetime] = None,
    step_minutes: int = STEP_MINUTES_DEFAULT,
) -> list[Measurement]:
    n = len(next(iter(values.values())))
    start_time = start_time or datetime.now(timezone.utc)
    out = []
    for i in range(n):
        ts = (start_time + timedelta(minutes=step_minutes * i)).isoformat()
        out.append(
            Measurement(
                station_id=station_id,
                station_name=station_name,
                timestamp=ts,
                pm10=values.get("pm10", [None] * n)[i],
                pm25=values.get("pm25", [None] * n)[i],
                no2=values.get("no2", [None] * n)[i],
                o3=values.get("o3", [None] * n)[i],
                so2=values.get("so2", [None] * n)[i],
                co=values.get("co", [None] * n)[i],
            )
        )
    return out


def generate_scenario(
    intent: ScenarioIntent,
    rng: random.Random,
    n: int = 12,
    station_id: str = "sim-1",
    station_name: str = "Stacja symulowana",
    start_time: Optional[datetime] = None,
) -> list[Measurement]:
    pm10: list[Optional[float]]
    pm25: list[Optional[float]]

    if intent == ScenarioIntent.TYPICAL:
        base10 = rng.uniform(10, 30)
        base25 = rng.uniform(4, 12)
        pm10 = [_clip_positive(rng.gauss(base10, base10 * 0.08)) for _ in range(n)]
        pm25 = [_clip_positive(rng.gauss(base25, base25 * 0.08)) for _ in range(n)]

    elif intent == ScenarioIntent.ELEVATED:
        base10 = rng.uniform(50, 110)
        base25 = rng.uniform(18, 40)
        pm10 = [_clip_positive(rng.gauss(base10, base10 * 0.08)) for _ in range(n)]
        pm25 = [_clip_positive(rng.gauss(base25, base25 * 0.08)) for _ in range(n)]

    elif intent == ScenarioIntent.RAPID_WORSENING:
        start10 = rng.uniform(15, 40)
        peak10 = rng.uniform(160, 260)
        jump_at = rng.randint(1, max(1, n // 3))
        pm10 = [
            _clip_positive(rng.gauss(start10, start10 * 0.05)) if i < jump_at
            else _clip_positive(rng.gauss(peak10, peak10 * 0.06))
            for i in range(n)
        ]
        start25 = rng.uniform(6, 12)
        peak25 = rng.uniform(55, 90)
        pm25 = [
            _clip_positive(rng.gauss(start25, start25 * 0.05)) if i < jump_at
            else _clip_positive(rng.gauss(peak25, peak25 * 0.06))
            for i in range(n)
        ]

    elif intent == ScenarioIntent.IMPROVEMENT:
        start10 = rng.uniform(60, 140)
        end10 = rng.uniform(10, 35)
        drop_at = rng.randint(1, max(1, n // 3))
        pm10 = [
            _clip_positive(rng.gauss(start10, start10 * 0.05)) if i < drop_at
            else _clip_positive(rng.gauss(end10, end10 * 0.08))
            for i in range(n)
        ]
        start25 = rng.uniform(20, 45)
        end25 = rng.uniform(4, 12)
        pm25 = [
            _clip_positive(rng.gauss(start25, start25 * 0.05)) if i < drop_at
            else _clip_positive(rng.gauss(end25, end25 * 0.08))
            for i in range(n)
        ]

    elif intent == ScenarioIntent.UNSTABLE:
        base10 = rng.uniform(20, 90)
        base25 = rng.uniform(8, 30)
        pm10 = [_clip_positive(base10 + rng.uniform(-1, 1) * base10 * rng.uniform(0.6, 1.4)) for _ in range(n)]
        pm25 = [_clip_positive(base25 + rng.uniform(-1, 1) * base25 * rng.uniform(0.6, 1.4)) for _ in range(n)]

    elif intent == ScenarioIntent.INSUFFICIENT_DATA:
        if rng.random() < 0.5:
            n = rng.randint(1, 5)
            base10 = rng.uniform(10, 60)
            pm10 = [_clip_positive(rng.gauss(base10, base10 * 0.1)) for _ in range(n)]
            pm25 = [_clip_positive(rng.gauss(base10 * 0.35, 2)) for _ in range(n)]
        else:
            base10 = rng.uniform(10, 60)
            pm10 = [
                None if rng.random() < 0.6 else _clip_positive(rng.gauss(base10, base10 * 0.1))
                for _ in range(n)
            ]
            pm25 = [
                None if rng.random() < 0.6 else _clip_positive(rng.gauss(base10 * 0.35, 2))
                for _ in range(n)
            ]
    else:
        raise ValueError(f"Nieznany scenariusz: {intent}")

    return _build_measurements(
        {"pm10": pm10, "pm25": pm25},
        station_id=station_id,
        station_name=station_name,
        start_time=start_time,
    )


class LiveStationSimulator:
    def __init__(self, station_id: str, station_name: str, seed: Optional[int] = None):
        self.station_id = station_id
        self.station_name = station_name
        self.rng = random.Random(seed)
        self._current_intent: Optional[ScenarioIntent] = None
        self._remaining = 0
        self._pick_new_intent()

    def _pick_new_intent(self) -> None:
        weights = {
            ScenarioIntent.TYPICAL: 5,
            ScenarioIntent.ELEVATED: 3,
            ScenarioIntent.RAPID_WORSENING: 1,
            ScenarioIntent.IMPROVEMENT: 1,
            ScenarioIntent.UNSTABLE: 2,
            ScenarioIntent.INSUFFICIENT_DATA: 1,
        }
        intents = list(weights.keys())
        self._current_intent = self.rng.choices(intents, weights=list(weights.values()))[0]
        self._remaining = self.rng.randint(15, 40)
        self._buffer = generate_scenario(
            self._current_intent,
            self.rng,
            n=self._remaining,
            station_id=self.station_id,
            station_name=self.station_name,
        )
        self._buffer_idx = 0

    def next_measurement(self) -> Measurement:
        if self._buffer_idx >= len(self._buffer):
            self._pick_new_intent()
        m = self._buffer[self._buffer_idx]
        m.timestamp = datetime.now(timezone.utc).isoformat()
        self._buffer_idx += 1
        return m
