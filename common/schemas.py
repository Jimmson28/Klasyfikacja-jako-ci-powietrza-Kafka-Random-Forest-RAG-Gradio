from __future__ import annotations

from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from typing import Optional


def utcnow_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


@dataclass
class Measurement:
    station_id: str
    station_name: str
    timestamp: str
    pm10: Optional[float] = None
    pm25: Optional[float] = None
    no2: Optional[float] = None
    o3: Optional[float] = None
    so2: Optional[float] = None
    co: Optional[float] = None

    def to_dict(self) -> dict:
        return asdict(self)

    @staticmethod
    def from_dict(d: dict) -> "Measurement":
        return Measurement(
            station_id=d["station_id"],
            station_name=d.get("station_name", d["station_id"]),
            timestamp=d["timestamp"],
            pm10=d.get("pm10"),
            pm25=d.get("pm25"),
            no2=d.get("no2"),
            o3=d.get("o3"),
            so2=d.get("so2"),
            co=d.get("co"),
        )


@dataclass
class PollutantStats:
    n: int = 0
    missing: int = 0
    mean: Optional[float] = None
    std: Optional[float] = None
    min: Optional[float] = None
    max: Optional[float] = None
    first: Optional[float] = None
    last: Optional[float] = None
    cv: Optional[float] = None
    pct_change: Optional[float] = None

    def to_dict(self) -> dict:
        return asdict(self)


@dataclass
class WindowFeatures:
    station_id: str
    station_name: str
    window_start: str
    window_end: str
    window_size: int
    n_present: int
    missing_ratio: float
    stats: dict

    def to_dict(self) -> dict:
        d = asdict(self)
        return d

    @staticmethod
    def from_dict(d: dict) -> "WindowFeatures":
        return WindowFeatures(**d)

    def flat_vector(self, pollutants: list[str]) -> list[float]:
        out: list[float] = [self.missing_ratio, float(self.n_present)]
        for p in pollutants:
            s = self.stats.get(p, {})
            for key in ("mean", "std", "min", "max", "cv", "pct_change"):
                v = s.get(key)
                out.append(float(v) if v is not None else 0.0)
        return out


@dataclass
class ClassificationResult:
    station_id: str
    station_name: str
    window_start: str
    window_end: str
    features: dict
    rule_label: str
    rule_reasons: list[str]
    model_label: str
    model_confidence: float
    agreement: bool
    classified_at: str = field(default_factory=utcnow_iso)

    def to_dict(self) -> dict:
        return asdict(self)

    @staticmethod
    def from_dict(d: dict) -> "ClassificationResult":
        return ClassificationResult(**d)
