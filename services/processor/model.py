from __future__ import annotations

import logging
from pathlib import Path
from typing import Optional

import joblib

from common import config
from common.schemas import WindowFeatures

logger = logging.getLogger(__name__)


class RandomForestModel:
    def __init__(self, model_path: str = config.RF_MODEL_PATH):
        self.model_path = model_path
        self.clf = None
        self._load()

    def _load(self) -> None:
        path = Path(self.model_path)
        if not path.exists():
            logger.warning(
                "Nie znaleziono modelu Random Forest pod %s. Processor będzie "
                "publikował klasę wyłącznie na podstawie metodyki reguł "
                "(common.rules), dopóki model nie zostanie wytrenowany "
                "(python -m ml.generate_training_data && python -m ml.train_random_forest) "
                "i zamontowany pod tą ścieżką.",
                self.model_path,
            )
            return
        self.clf = joblib.load(path)
        logger.info("Wczytano model Random Forest z %s (klasy: %s)", self.model_path, list(self.clf.classes_))

    @property
    def available(self) -> bool:
        return self.clf is not None

    def predict(self, features: WindowFeatures) -> tuple[Optional[str], float]:
        if not self.available:
            return None, 0.0
        vector = features.flat_vector(config.PRIMARY_POLLUTANTS)
        proba = self.clf.predict_proba([vector])[0]
        best_idx = proba.argmax()
        label = self.clf.classes_[best_idx]
        confidence = float(proba[best_idx])
        return label, confidence

    def reload(self) -> None:
        self._load()
