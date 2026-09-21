from __future__ import annotations

import statistics
from typing import Optional

from common import config
from common.schemas import Measurement, PollutantStats, WindowFeatures


def _pollutant_stats(values: list[Optional[float]]) -> PollutantStats:
    n_total = len(values)
    present = [v for v in values if v is not None]
    n = len(present)
    missing = n_total - n

    if n == 0:
        return PollutantStats(n=0, missing=missing)

    mean = statistics.fmean(present)
    std = statistics.pstdev(present) if n >= 2 else 0.0
    cv = (std / mean) if mean not in (0, 0.0) else 0.0

    first = next((v for v in values if v is not None), None)
    last = next((v for v in reversed(values) if v is not None), None)
    pct_change = 0.0
    if first not in (None, 0, 0.0) and last is not None:
        pct_change = (last - first) / first

    return PollutantStats(
        n=n,
        missing=missing,
        mean=mean,
        std=std,
        min=min(present),
        max=max(present),
        first=first,
        last=last,
        cv=cv,
        pct_change=pct_change,
    )


def compute_features(measurements: list[Measurement]) -> WindowFeatures:
    if not measurements:
        raise ValueError("compute_features wymaga co najmniej jednego pomiaru")

    station_id = measurements[-1].station_id
    station_name = measurements[-1].station_name
    window_start = measurements[0].timestamp
    window_end = measurements[-1].timestamp
    window_size_actual = len(measurements)

    stats: dict[str, dict] = {}
    for pollutant in config.ALL_POLLUTANTS:
        values = [getattr(m, pollutant) for m in measurements]
        stats[pollutant] = _pollutant_stats(values).to_dict()

    primary_missing_ratios = []
    for pollutant in config.PRIMARY_POLLUTANTS:
        missing = stats[pollutant]["missing"]
        primary_missing_ratios.append(missing / window_size_actual)
    missing_ratio = statistics.fmean(primary_missing_ratios) if primary_missing_ratios else 1.0

    return WindowFeatures(
        station_id=station_id,
        station_name=station_name,
        window_start=window_start,
        window_end=window_end,
        window_size=window_size_actual,
        n_present=window_size_actual,
        missing_ratio=missing_ratio,
        stats=stats,
    )
