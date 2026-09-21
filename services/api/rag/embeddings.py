from __future__ import annotations

import logging
import threading

from common import config

logger = logging.getLogger(__name__)

_lock = threading.Lock()
_model = None


def get_embedding_model():
    global _model
    if _model is None:
        with _lock:
            if _model is None:
                from sentence_transformers import SentenceTransformer

                logger.info("Ładowanie modelu embeddingów: %s", config.EMBEDDING_MODEL_NAME)
                _model = SentenceTransformer(config.EMBEDDING_MODEL_NAME)
    return _model


def embed_texts(texts: list[str]) -> list[list[float]]:
    model = get_embedding_model()
    vectors = model.encode(texts, normalize_embeddings=True, show_progress_bar=False)
    return [v.tolist() for v in vectors]


def embed_text(text: str) -> list[float]:
    return embed_texts([text])[0]


def embedding_dim() -> int:
    return get_embedding_model().get_sentence_embedding_dimension()
