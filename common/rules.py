from __future__ import annotations

from typing import Optional

from common import config
from common.schemas import WindowFeatures


def _get(features: WindowFeatures, pollutant: str, key: str) -> Optional[float]:
    return features.stats.get(pollutant, {}).get(key)


def classify_window(features: WindowFeatures) -> tuple[str, list[str]]:
    reasons: list[str] = []

    if features.window_size < config.MIN_SAMPLES_IN_WINDOW:
        reasons.append(
            f"Za mało pomiarów w oknie: {features.window_size} < "
            f"wymagane minimum {config.MIN_SAMPLES_IN_WINDOW}."
        )
        return config.LABEL_INSUFFICIENT_DATA, reasons

    if features.missing_ratio > config.MAX_MISSING_RATIO:
        reasons.append(
            f"Zbyt wysoki odsetek brakujących wartości pyłów: "
            f"{features.missing_ratio:.0%} > próg {config.MAX_MISSING_RATIO:.0%}."
        )
        return config.LABEL_INSUFFICIENT_DATA, reasons

    pm10_mean = _get(features, "pm10", "mean")
    pm25_mean = _get(features, "pm25", "mean")
    pm10_cv = _get(features, "pm10", "cv")
    pm25_cv = _get(features, "pm25", "cv")
    pm10_pct = _get(features, "pm10", "pct_change")
    pm25_pct = _get(features, "pm25", "pct_change")
    pm10_first = _get(features, "pm10", "first")
    pm25_first = _get(features, "pm25", "first")
    pm10_last = _get(features, "pm10", "last")
    pm25_last = _get(features, "pm25", "last")

    if (pm10_cv is not None and pm10_cv > config.CV_UNSTABLE_THRESHOLD) or (
        pm25_cv is not None and pm25_cv > config.CV_UNSTABLE_THRESHOLD
    ):
        if pm10_cv is not None and pm10_cv > config.CV_UNSTABLE_THRESHOLD:
            reasons.append(
                f"Wysoka zmienność PM10 w oknie: CV={pm10_cv:.2f} > "
                f"próg {config.CV_UNSTABLE_THRESHOLD:.2f}."
            )
        if pm25_cv is not None and pm25_cv > config.CV_UNSTABLE_THRESHOLD:
            reasons.append(
                f"Wysoka zmienność PM2.5 w oknie: CV={pm25_cv:.2f} > "
                f"próg {config.CV_UNSTABLE_THRESHOLD:.2f}."
            )
        return config.LABEL_UNSTABLE, reasons

    if pm10_pct is not None and pm10_pct >= config.RAPID_CHANGE_PCT and (
        pm10_last is not None and pm10_last >= config.PM10_ALERT
    ):
        reasons.append(
            f"Gwałtowny wzrost PM10 o {pm10_pct:.0%} w obrębie okna, "
            f"osiągając {pm10_last:.1f} µg/m3 (próg alarmowy {config.PM10_ALERT:.0f})."
        )
        return config.LABEL_RAPID_WORSENING, reasons

    if pm25_pct is not None and pm25_pct >= config.RAPID_CHANGE_PCT and (
        pm25_last is not None and pm25_last >= config.PM25_ALERT
    ):
        reasons.append(
            f"Gwałtowny wzrost PM2.5 o {pm25_pct:.0%} w obrębie okna, "
            f"osiągając {pm25_last:.1f} µg/m3 (próg alarmowy {config.PM25_ALERT:.0f})."
        )
        return config.LABEL_RAPID_WORSENING, reasons

    if pm10_pct is not None and pm10_pct <= -config.RAPID_CHANGE_PCT and (
        pm10_first is not None and pm10_first >= config.PM10_TYPICAL_MAX
    ):
        reasons.append(
            f"Wyraźny spadek PM10 o {pm10_pct:.0%} względem początku okna "
            f"({pm10_first:.1f} µg/m3), wracając w kierunku wartości typowych."
        )
        return config.LABEL_IMPROVEMENT, reasons

    if pm25_pct is not None and pm25_pct <= -config.RAPID_CHANGE_PCT and (
        pm25_first is not None and pm25_first >= config.PM25_TYPICAL_MAX
    ):
        reasons.append(
            f"Wyraźny spadek PM2.5 o {pm25_pct:.0%} względem początku okna "
            f"({pm25_first:.1f} µg/m3), wracając w kierunku wartości typowych."
        )
        return config.LABEL_IMPROVEMENT, reasons

    if (pm10_mean is not None and pm10_mean > config.PM10_TYPICAL_MAX) or (
        pm25_mean is not None and pm25_mean > config.PM25_TYPICAL_MAX
    ):
        if pm10_mean is not None and pm10_mean > config.PM10_TYPICAL_MAX:
            reasons.append(
                f"Średnie PM10 w oknie {pm10_mean:.1f} µg/m3 > "
                f"wartość referencyjna WHO {config.PM10_TYPICAL_MAX:.0f} µg/m3."
            )
        if pm25_mean is not None and pm25_mean > config.PM25_TYPICAL_MAX:
            reasons.append(
                f"Średnie PM2.5 w oknie {pm25_mean:.1f} µg/m3 > "
                f"wartość referencyjna WHO {config.PM25_TYPICAL_MAX:.0f} µg/m3."
            )
        return config.LABEL_ELEVATED, reasons

    reasons.append(
        "Stężenia pyłów w granicach wartości referencyjnych WHO, "
        "niska zmienność, brak istotnego trendu."
    )
    return config.LABEL_TYPICAL, reasons
