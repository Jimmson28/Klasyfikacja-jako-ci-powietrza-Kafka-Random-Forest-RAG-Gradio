from __future__ import annotations

import logging

from common import config
from common.schemas import ClassificationResult

logger = logging.getLogger(__name__)


def _build_query(result: ClassificationResult) -> str:
    label_name = config.LABEL_DISPLAY_NAMES.get(result.model_label, result.model_label)
    return f"Klasa stanu jakości powietrza: {label_name}. {' '.join(result.rule_reasons)}"


def retrieve_context(result: ClassificationResult, top_k: int = 3) -> list[dict]:
    try:
        from services.api.rag import embeddings, milvus_store

        query = _build_query(result)
        query_vector = embeddings.embed_text(query)
        return milvus_store.search(query_vector, top_k=top_k)
    except Exception:
        logger.exception("Nie udało się pobrać kontekstu RAG z Milvus - kontynuuję bez kontekstu.")
        return []
