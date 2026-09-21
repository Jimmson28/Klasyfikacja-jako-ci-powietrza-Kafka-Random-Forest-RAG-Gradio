from __future__ import annotations

import json
import sqlite3
import threading
from pathlib import Path

from common import config
from common.schemas import ClassificationResult

_write_lock = threading.Lock()

SCHEMA = """
CREATE TABLE IF NOT EXISTS classifications (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    station_id TEXT NOT NULL,
    station_name TEXT NOT NULL,
    window_start TEXT NOT NULL,
    window_end TEXT NOT NULL,
    rule_label TEXT NOT NULL,
    model_label TEXT NOT NULL,
    model_confidence REAL NOT NULL,
    agreement INTEGER NOT NULL,
    features_json TEXT NOT NULL,
    rule_reasons_json TEXT NOT NULL,
    explanation TEXT,
    explanation_source TEXT,
    classified_at TEXT NOT NULL,
    created_at TEXT NOT NULL DEFAULT (datetime('now'))
);
CREATE INDEX IF NOT EXISTS idx_station_time ON classifications(station_id, classified_at DESC);
"""


def _connect() -> sqlite3.Connection:
    Path(config.SQLITE_PATH).parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(config.SQLITE_PATH, check_same_thread=False, timeout=30)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA journal_mode=WAL")
    conn.execute("PRAGMA busy_timeout=30000")
    return conn


def init_db() -> None:
    with _connect() as conn:
        conn.executescript(SCHEMA)


def insert_classification(result: ClassificationResult, explanation: str, explanation_source: str) -> int:
    with _write_lock, _connect() as conn:
        cur = conn.execute(
            """
            INSERT INTO classifications (
                station_id, station_name, window_start, window_end,
                rule_label, model_label, model_confidence, agreement,
                features_json, rule_reasons_json, explanation, explanation_source, classified_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                result.station_id,
                result.station_name,
                result.window_start,
                result.window_end,
                result.rule_label,
                result.model_label,
                result.model_confidence,
                int(result.agreement),
                json.dumps(result.features, ensure_ascii=False),
                json.dumps(result.rule_reasons, ensure_ascii=False),
                explanation,
                explanation_source,
                result.classified_at,
            ),
        )
        return cur.lastrowid


def insert_pending(result: ClassificationResult) -> int:
    return insert_classification(result, explanation=None, explanation_source="pending")


def update_explanation(row_id: int, explanation: str, explanation_source: str) -> None:
    with _write_lock, _connect() as conn:
        conn.execute(
            "UPDATE classifications SET explanation = ?, explanation_source = ? WHERE id = ?",
            (explanation, explanation_source, row_id),
        )


def _row_to_dict(row: sqlite3.Row) -> dict:
    d = dict(row)
    d["agreement"] = bool(d["agreement"])
    d["features"] = json.loads(d.pop("features_json"))
    d["rule_reasons"] = json.loads(d.pop("rule_reasons_json"))
    return d


def get_latest_for_station(station_id: str) -> dict | None:
    with _connect() as conn:
        row = conn.execute(
            "SELECT * FROM classifications WHERE station_id = ? ORDER BY id DESC LIMIT 1",
            (station_id,),
        ).fetchone()
        return _row_to_dict(row) if row else None


def get_history_for_station(station_id: str, limit: int = 50) -> list[dict]:
    with _connect() as conn:
        rows = conn.execute(
            "SELECT * FROM classifications WHERE station_id = ? ORDER BY id DESC LIMIT ?",
            (station_id, limit),
        ).fetchall()
        return [_row_to_dict(r) for r in rows]


def list_known_stations() -> list[dict]:
    with _connect() as conn:
        rows = conn.execute(
            """
            SELECT station_id, station_name, MAX(classified_at) AS last_seen
            FROM classifications GROUP BY station_id ORDER BY station_name
            """
        ).fetchall()
        return [dict(r) for r in rows]


def get_latest_overview() -> list[dict]:
    stations = list_known_stations()
    return [get_latest_for_station(s["station_id"]) for s in stations]


def get_latest_fallback_row() -> dict | None:
    with _connect() as conn:
        row = conn.execute(
            "SELECT * FROM classifications WHERE explanation_source = 'fallback_template' "
            "ORDER BY id DESC LIMIT 1"
        ).fetchone()
        return _row_to_dict(row) if row else None


def get_next_enrichment_candidate(after_station_id: str | None) -> dict | None:
    with _connect() as conn:
        rows = conn.execute(
            """
            SELECT c1.* FROM classifications c1
            WHERE c1.explanation_source = 'fallback_template'
              AND c1.id = (
                SELECT MAX(c2.id) FROM classifications c2
                WHERE c2.station_id = c1.station_id AND c2.explanation_source = 'fallback_template'
              )
            ORDER BY c1.station_id
            """
        ).fetchall()

    if not rows:
        return None

    candidates = [_row_to_dict(r) for r in rows]
    if after_station_id is None:
        return candidates[0]
    for candidate in candidates:
        if candidate["station_id"] > after_station_id:
            return candidate
    return candidates[0]


def count_fallback_since(cutoff_iso: str) -> int:
    with _connect() as conn:
        row = conn.execute(
            "SELECT COUNT(*) AS n FROM classifications "
            "WHERE explanation_source = 'fallback_template' AND classified_at > ?",
            (cutoff_iso,),
        ).fetchone()
        return row["n"] if row else 0
