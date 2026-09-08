from __future__ import annotations

import os
import sqlite3
from contextlib import contextmanager
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Iterator


# ============================================================
# Database configuration
# ============================================================

# Vercel Functions have a writable temporary directory at /tmp.
# For local development, use the project's data directory.
VERCEL_ENV = os.getenv("VERCEL", "").lower() == "1"

if VERCEL_ENV:
    DEFAULT_PATH = "/tmp/personal_assistant.db"
else:
    DEFAULT_PATH = "data/personal_assistant.db"


# Allow an explicit DATABASE_PATH, but protect Vercel from
# accidentally receiving a non-writable project path.
configured_path = os.getenv("DATABASE_PATH", "").strip()

if VERCEL_ENV:
    if configured_path and configured_path.startswith("/tmp/"):
        DATABASE_PATH = Path(configured_path)
    else:
        DATABASE_PATH = Path(DEFAULT_PATH)
else:
    DATABASE_PATH = Path(configured_path or DEFAULT_PATH)


# ============================================================
# Time
# ============================================================

def now() -> str:
    """Return the current UTC time as an ISO-8601 string."""
    return datetime.now(timezone.utc).isoformat()


# ============================================================
# Database connection
# ============================================================

@contextmanager
def connection() -> Iterator[sqlite3.Connection]:
    """
    Open a SQLite connection safely.

    On Vercel, the database is stored in /tmp because the deployed
    application's project filesystem is not intended for writes.
    """

    database_parent = DATABASE_PATH.parent

    # Make sure the parent directory exists.
    database_parent.mkdir(parents=True, exist_ok=True)

    conn: sqlite3.Connection | None = None

    try:
        conn = sqlite3.connect(
            str(DATABASE_PATH),
            timeout=30,
        )

        conn.row_factory = sqlite3.Row

        yield conn

        conn.commit()

    except Exception:
        if conn is not None:
            conn.rollback()
        raise

    finally:
        if conn is not None:
            conn.close()


# ============================================================
# Database initialization
# ============================================================

def init_database() -> None:
    """Create all required database tables and indexes."""

    with connection() as conn:

        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS users (
                user_id INTEGER PRIMARY KEY,
                username TEXT,
                first_name TEXT,
                last_name TEXT,
                created_at TEXT NOT NULL,
                updated_at TEXT NOT NULL
            )
            """
        )

        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS messages (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER NOT NULL,
                direction TEXT NOT NULL
                    CHECK(direction IN ('in', 'out')),
                content TEXT NOT NULL,
                created_at TEXT NOT NULL
            )
            """
        )

        conn.execute(
            """
            CREATE INDEX IF NOT EXISTS idx_messages_user
            ON messages(user_id, id DESC)
            """
        )


# ============================================================
# Users
# ============================================================

def save_user(user: dict[str, Any]) -> None:
    """Insert or update a Telegram user."""

    user_id = user.get("id")

    if not user_id:
        return

    timestamp = now()

    with connection() as conn:
        conn.execute(
            """
            INSERT INTO users(
                user_id,
                username,
                first_name,
                last_name,
                created_at,
                updated_at
            )
            VALUES (?, ?, ?, ?, ?, ?)

            ON CONFLICT(user_id) DO UPDATE SET
                username=excluded.username,
                first_name=excluded.first_name,
                last_name=excluded.last_name,
                updated_at=excluded.updated_at
            """,
            (
                user_id,
                user.get("username", ""),
                user.get("first_name", ""),
                user.get("last_name", ""),
                timestamp,
                timestamp,
            ),
        )


# ============================================================
# Messages
# ============================================================

def save_message(
    user_id: int,
    direction: str,
    content: str,
) -> None:
    """Save an incoming or outgoing message."""

    if direction not in ("in", "out"):
        raise ValueError(
            "direction must be either 'in' or 'out'"
        )

    with connection() as conn:
        conn.execute(
            """
            INSERT INTO messages(
                user_id,
                direction,
                content,
                created_at
            )
            VALUES (?, ?, ?, ?)
            """,
            (
                user_id,
                direction,
                content,
                now(),
            ),
        )


# ============================================================
# Conversation history
# ============================================================

def recent_messages(
    user_id: int,
    limit: int = 8,
) -> list[dict[str, str]]:
    """Return the most recent messages for a user."""

    # Prevent invalid or unnecessarily large limits.
    try:
        limit = int(limit)
    except (TypeError, ValueError):
        limit = 8

    limit = max(1, min(limit, 100))

    with connection() as conn:
        rows = conn.execute(
            """
            SELECT direction, content
            FROM messages
            WHERE user_id = ?
            ORDER BY id DESC
            LIMIT ?
            """,
            (
                user_id,
                limit,
            ),
        ).fetchall()

    return [
        {
            "role": (
                "user"
                if row["direction"] == "in"
                else "assistant"
            ),
            "content": row["content"],
        }
        for row in reversed(rows)
    ]


# ============================================================
# Clear conversation
# ============================================================

def clear_messages(user_id: int) -> None:
    """Delete the conversation history of a user."""

    with connection() as conn:
        conn.execute(
            """
            DELETE FROM messages
            WHERE user_id = ?
            """,
            (user_id,),
        )