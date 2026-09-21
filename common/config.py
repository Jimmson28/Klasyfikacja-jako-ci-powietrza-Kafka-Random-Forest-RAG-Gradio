from __future__ import annotations

import os


def _env_float(name: str, default: float) -> float:
    return float(os.environ.get(name, default))


def _env_int(name: str, default: int) -> int:
    return int(os.environ.get(name, default))


WINDOW_SIZE = _env_int("WINDOW_SIZE", 12)
MIN_SAMPLES_IN_WINDOW = _env_int("MIN_SAMPLES_IN_WINDOW", 6)

MAX_MISSING_RATIO = _env_float("MAX_MISSING_RATIO", 0.30)

PM10_TYPICAL_MAX = _env_float("PM10_TYPICAL_MAX", 45.0)
PM25_TYPICAL_MAX = _env_float("PM25_TYPICAL_MAX", 15.0)

PM10_ALERT = _env_float("PM10_ALERT", 150.0)
PM25_ALERT = _env_float("PM25_ALERT", 50.0)

CV_UNSTABLE_THRESHOLD = _env_float("CV_UNSTABLE_THRESHOLD", 0.5)

RAPID_CHANGE_PCT = _env_float("RAPID_CHANGE_PCT", 0.5)

PRIMARY_POLLUTANTS = ["pm10", "pm25"]
ALL_POLLUTANTS = ["pm10", "pm25", "no2", "o3", "so2", "co"]

LABEL_TYPICAL = "typowy_profil_pomiarowy"
LABEL_ELEVATED = "podwyzszone_stezenie_pylow"
LABEL_RAPID_WORSENING = "gwaltowne_pogorszenie"
LABEL_IMPROVEMENT = "poprawa"
LABEL_UNSTABLE = "niestabilny_pomiar"
LABEL_INSUFFICIENT_DATA = "niewystarczajace_dane"

ALL_LABELS = [
    LABEL_TYPICAL,
    LABEL_ELEVATED,
    LABEL_RAPID_WORSENING,
    LABEL_IMPROVEMENT,
    LABEL_UNSTABLE,
    LABEL_INSUFFICIENT_DATA,
]

LABEL_DISPLAY_NAMES = {
    LABEL_TYPICAL: "Typowy profil pomiarowy",
    LABEL_ELEVATED: "Podwyższone stężenie pyłów",
    LABEL_RAPID_WORSENING: "Gwałtowne pogorszenie",
    LABEL_IMPROVEMENT: "Poprawa",
    LABEL_UNSTABLE: "Niestabilny pomiar",
    LABEL_INSUFFICIENT_DATA: "Niewystarczające dane",
}

KAFKA_BOOTSTRAP_SERVERS = os.environ.get("KAFKA_BOOTSTRAP_SERVERS", "localhost:9092")
TOPIC_RAW_MEASUREMENTS = os.environ.get("TOPIC_RAW_MEASUREMENTS", "air-quality-raw")
TOPIC_CLASSIFIED = os.environ.get("TOPIC_CLASSIFIED", "air-quality-classified")

MILVUS_URI = os.environ.get("MILVUS_URI", "/app/data/db/milvus_lite.db")
MILVUS_COLLECTION = os.environ.get("MILVUS_COLLECTION", "air_quality_kb")

EMBEDDING_MODEL_NAME = os.environ.get(
    "EMBEDDING_MODEL_NAME", "sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2"
)
HF_LLM_MODEL = os.environ.get("HF_LLM_MODEL", "Qwen/Qwen2.5-0.5B-Instruct")
RF_MODEL_PATH = os.environ.get("RF_MODEL_PATH", "/app/ml_models/random_forest.joblib")

SQLITE_PATH = os.environ.get("SQLITE_PATH", "/app/data/db/classifications.db")
