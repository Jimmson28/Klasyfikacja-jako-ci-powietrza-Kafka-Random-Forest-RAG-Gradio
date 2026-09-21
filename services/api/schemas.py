from __future__ import annotations

from pydantic import BaseModel, Field


class MeasurementIn(BaseModel):
    pm10: float | None = None
    pm25: float | None = None
    no2: float | None = None
    o3: float | None = None
    so2: float | None = None
    co: float | None = None


class ManualClassifyRequest(BaseModel):
    station_id: str = "manual-test"
    station_name: str = "Test manualny"
    measurements: list[MeasurementIn] = Field(..., min_length=1, max_length=50)
