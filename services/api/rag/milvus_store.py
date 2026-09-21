from __future__ import annotations

import logging
import threading
from pathlib import Path

from common import config

logger = logging.getLogger(__name__)

_client = None
_loaded = False
_lock = threading.Lock()


def _is_server_uri(uri: str) -> bool:
    return uri.startswith(("http://", "https://"))


def _get_client():
    global _client
    if _client is None:
        with _lock:
            if _client is None:
                from pymilvus import MilvusClient

                uri = config.MILVUS_URI
                if not _is_server_uri(uri):
                    Path(uri).parent.mkdir(parents=True, exist_ok=True)
                _client = MilvusClient(uri=uri)
                logger.info("Połączono z Milvus (%s)", uri)
    return _client


def ensure_collection(dim: int):
    global _loaded
    client = _get_client()

    if not client.has_collection(config.MILVUS_COLLECTION):
        from pymilvus import DataType

        schema = client.create_schema(auto_id=True, enable_dynamic_field=False)
        schema.add_field(field_name="id", datatype=DataType.INT64, is_primary=True, auto_id=True)
        schema.add_field(field_name="text", datatype=DataType.VARCHAR, max_length=4000)
        schema.add_field(field_name="source", datatype=DataType.VARCHAR, max_length=256)
        schema.add_field(field_name="embedding", datatype=DataType.FLOAT_VECTOR, dim=dim)

        index_params = client.prepare_index_params()
        index_params.add_index(field_name="embedding", index_type="AUTOINDEX", metric_type="COSINE")

        client.create_collection(collection_name=config.MILVUS_COLLECTION, schema=schema, index_params=index_params)
        logger.info("Utworzono kolekcję Milvus '%s' (dim=%d)", config.MILVUS_COLLECTION, dim)
        _loaded = True
    elif not _loaded:
        client.load_collection(config.MILVUS_COLLECTION)
        _loaded = True

    return client


def count_entities() -> int:
    client = _get_client()
    if not client.has_collection(config.MILVUS_COLLECTION):
        return 0
    rows = client.query(config.MILVUS_COLLECTION, filter="", output_fields=["count(*)"])
    return int(rows[0]["count(*)"]) if rows else 0


def insert_documents(chunks: list[dict], embeddings: list[list[float]]) -> None:
    if not chunks:
        return
    client = ensure_collection(dim=len(embeddings[0]))
    data = [{"text": c["text"], "source": c["source"], "embedding": e} for c, e in zip(chunks, embeddings)]
    client.insert(collection_name=config.MILVUS_COLLECTION, data=data)
    logger.info("Zaindeksowano %d fragmentów w Milvus.", len(chunks))


def search(query_embedding: list[float], top_k: int = 3) -> list[dict]:
    client = ensure_collection(dim=len(query_embedding))
    results = client.search(
        collection_name=config.MILVUS_COLLECTION,
        data=[query_embedding],
        limit=top_k,
        output_fields=["text", "source"],
    )
    hits = []
    for hit in results[0]:
        entity = hit.get("entity", {})
        hits.append({"text": entity.get("text"), "source": entity.get("source"), "score": float(hit.get("distance", 0.0))})
    return hits
