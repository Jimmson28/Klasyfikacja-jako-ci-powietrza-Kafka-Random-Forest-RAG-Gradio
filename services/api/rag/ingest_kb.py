from __future__ import annotations

import logging
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

KB_DIR = ROOT / "data" / "knowledge_base"

logger = logging.getLogger(__name__)


def _chunk_markdown_file(path: Path) -> list[dict]:
    text = path.read_text(encoding="utf-8")
    paragraphs = [p.strip() for p in text.split("\n\n") if p.strip()]
    if not paragraphs:
        return []

    title = paragraphs[0].lstrip("#").strip()
    body_paragraphs = paragraphs[1:] or paragraphs

    chunks = []
    for paragraph in body_paragraphs:
        chunks.append({"text": f"{title}: {paragraph}", "source": path.name})
    return chunks


def load_all_chunks() -> list[dict]:
    chunks = []
    for path in sorted(KB_DIR.glob("*.md")):
        chunks.extend(_chunk_markdown_file(path))
    return chunks


def ensure_ingested(force: bool = False) -> int:
    from services.api.rag import embeddings, milvus_store

    if not force:
        existing = milvus_store.count_entities()
        if existing > 0:
            logger.info("Baza wiedzy RAG już zaindeksowana (%d fragmentów) - pomijam ingest.", existing)
            return existing

    chunks = load_all_chunks()
    if not chunks:
        logger.warning("Brak plików w %s - baza wiedzy RAG będzie pusta.", KB_DIR)
        return 0

    texts = [c["text"] for c in chunks]
    vectors = embeddings.embed_texts(texts)
    milvus_store.insert_documents(chunks, vectors)
    logger.info("Zaindeksowano %d fragmentów bazy wiedzy z %s.", len(chunks), KB_DIR)
    return len(chunks)


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    ensure_ingested(force="--force" in sys.argv)
