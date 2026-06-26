"""SQLite database layer for the BetterHackdays matchmaking backend.

A tiny, dependency-free SQLite wrapper. List-typed columns (skills, interests,
looking_for, harness_ids) are stored as JSON strings.

The same module is imported by the REST layer and the MCP-friendly function
layer so both surfaces share one source of truth.
"""

from __future__ import annotations

import json
import os
import sqlite3
from contextlib import contextmanager
from pathlib import Path
from typing import Any, Iterator

_SCHEMA = """
CREATE TABLE IF NOT EXISTS profiles (
    harness_id      TEXT PRIMARY KEY,
    display_label   TEXT NOT NULL DEFAULT 'New builder',
    skills          TEXT NOT NULL DEFAULT '[]',
    interests       TEXT NOT NULL DEFAULT '[]',
    preferred_role  TEXT,
    project_vibe    TEXT,
    looking_for     TEXT NOT NULL DEFAULT '[]',
    availability    TEXT,
    is_seeded       INTEGER NOT NULL DEFAULT 0,
    created_at      TEXT NOT NULL DEFAULT (datetime('now')),
    updated_at      TEXT NOT NULL DEFAULT (datetime('now'))
);

CREATE TABLE IF NOT EXISTS swipes (
    id              INTEGER PRIMARY KEY AUTOINCREMENT,
    from_harness_id TEXT NOT NULL,
    to_harness_id   TEXT NOT NULL,
    action          TEXT NOT NULL CHECK (action IN ('like', 'pass')),
    created_at      TEXT NOT NULL DEFAULT (datetime('now')),
    UNIQUE (from_harness_id, to_harness_id)
);

CREATE TABLE IF NOT EXISTS matches (
    match_id        TEXT PRIMARY KEY,
    harness_ids     TEXT NOT NULL,
    status          TEXT NOT NULL DEFAULT 'matched'
                    CHECK (status IN ('matched', 'proceeding', 'closed')),
    created_at      TEXT NOT NULL DEFAULT (datetime('now')),
    updated_at      TEXT NOT NULL DEFAULT (datetime('now'))
);

CREATE INDEX IF NOT EXISTS idx_swipes_from ON swipes (from_harness_id);
CREATE INDEX IF NOT EXISTS idx_swipes_to ON swipes (to_harness_id);
CREATE INDEX IF NOT EXISTS idx_matches_harness ON matches (harness_ids);
"""


def _db_path() -> str:
    """Resolve the SQLite path from DATABASE_URL or fall back to a local file."""
    url = os.getenv("DATABASE_URL", "sqlite:///./betterhackdays.db")
    if url.startswith("sqlite:///"):
        return url[len("sqlite:///"):]
    return url or "betterhackdays.db"


@contextmanager
def get_conn() -> Iterator[sqlite3.Connection]:
    """Yield a SQLite connection with row access by column name.

    Rows returned from this connection are dict-like via sqlite3.Row, but
    callers that need a plain dict should use `_row_to_dict`.
    """
    path = _db_path()
    Path(path).parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(path)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON;")
    try:
        yield conn
        conn.commit()
    except Exception:
        conn.rollback()
        raise
    finally:
        conn.close()


def init_db() -> None:
    """Create all tables and indices if they do not already exist."""
    with get_conn() as conn:
        conn.executescript(_SCHEMA)


def _row_to_dict(row: sqlite3.Row) -> dict[str, Any]:
    return {k: row[k] for k in row.keys()}


def _loads(value: Any, default: list[Any] | None = None) -> list[Any]:
    if default is None:
        default = []
    if value is None:
        return list(default)
    if isinstance(value, list):
        return value
    try:
        data = json.loads(value)
        return data if isinstance(data, list) else list(default)
    except (TypeError, ValueError):
        return list(default)


def _dumps(value: list[Any] | None) -> str:
    if value is None:
        return "[]"
    return json.dumps([str(v) for v in value], ensure_ascii=False)
