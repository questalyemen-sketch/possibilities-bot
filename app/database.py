from __future__ import annotations

import os
import sqlite3
from contextlib import contextmanager
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Iterator

DEFAULT_PATH = "/tmp/personal_assistant.db" if os.getenv("VERCEL") else "data/personal_assistant.db"
DATABASE_PATH = Path(os.getenv("DATABASE_PATH", DEFAULT_PATH))


def now() -> str:
    return datetime.now(timezone.utc).isoformat()


@contextmanager
def connection() -> Iterator[sqlite3.Connection]:
    DATABASE_PATH.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(DATABASE_PATH)
    conn.row_factory = sqlite3.Row
    try:
        yield conn
        conn.commit()
    finally:
        conn.close()


def init_database() -> None:
    with connection() as conn:
        conn.execute("""
            CREATE TABLE IF NOT EXISTS users (
                user_id INTEGER PRIMARY KEY,
                username TEXT,
                first_name TEXT,
                last_name TEXT,
                created_at TEXT NOT NULL,
                updated_at TEXT NOT NULL
            )
        """)
        conn.execute("""
            CREATE TABLE IF NOT EXISTS messages (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER NOT NULL,
                direction TEXT NOT NULL CHECK(direction IN ('in', 'out')),
                content TEXT NOT NULL,
                created_at TEXT NOT NULL
            )
        """)
        conn.execute("CREATE INDEX IF NOT EXISTS idx_messages_user ON messages(user_id, id DESC)")


def save_user(user: dict[str, Any]) -> None:
    timestamp = now()
    with connection() as conn:
        conn.execute("""
            INSERT INTO users(user_id, username, first_name, last_name, created_at, updated_at)
            VALUES (?, ?, ?, ?, ?, ?)
            ON CONFLICT(user_id) DO UPDATE SET
                username=excluded.username,
                first_name=excluded.first_name,
                last_name=excluded.last_name,
                updated_at=excluded.updated_at
        """, (
            user.get("id"),
            user.get("username", ""),
            user.get("first_name", ""),
            user.get("last_name", ""),
            timestamp,
            timestamp,
        ))


def save_message(user_id: int, direction: str, content: str) -> None:
    with connection() as conn:
        conn.execute(
            "INSERT INTO messages(user_id, direction, content, created_at) VALUES (?, ?, ?, ?)",
            (user_id, direction, content, now()),
        )


def recent_messages(user_id: int, limit: int = 8) -> list[dict[str, str]]:
    with connection() as conn:
        rows = conn.execute(
            "SELECT direction, content FROM messages WHERE user_id = ? ORDER BY id DESC LIMIT ?",
            (user_id, limit),
        ).fetchall()
    return [
        {"role": "user" if row["direction"] == "in" else "assistant", "content": row["content"]}
        for row in reversed(rows)
    ]


def clear_messages(user_id: int) -> None:
    with connection() as conn:
        conn.execute("DELETE FROM messages WHERE user_id = ?", (user_id,))
