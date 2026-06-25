"""SQLite-backed persistent storage for meeting history.

Schema is intentionally simple so external integrations (Notion, Jira, PDF)
can import Meeting and read from get_recent_meetings / get_meeting without
touching this module's internals.
"""

import json
import os
import sqlite3
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

DB_PATH = Path(os.getenv("DB_PATH", "meetings.db"))


@dataclass(frozen=True)
class Meeting:
    id: int
    user_id: int
    created_at: datetime
    transcript: str
    summary: str
    tasks: list[dict[str, Any]]
    deadlines: list[dict[str, Any]]
    notes: str


def init_db(db_path: Path = DB_PATH) -> None:
    """Create tables and indexes. Safe to call on every startup."""
    with sqlite3.connect(db_path) as conn:
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS meetings (
                id          INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id     INTEGER NOT NULL,
                created_at  TEXT    NOT NULL,
                transcript  TEXT    NOT NULL,
                summary     TEXT    NOT NULL,
                tasks       TEXT    NOT NULL,
                deadlines   TEXT    NOT NULL,
                notes       TEXT    NOT NULL
            )
            """
        )
        conn.execute(
            "CREATE INDEX IF NOT EXISTS idx_meetings_user_created "
            "ON meetings(user_id, created_at DESC)"
        )
        conn.commit()


def save_meeting(
    user_id: int,
    transcript: str,
    summary: str,
    tasks: list[dict[str, Any]],
    deadlines: list[dict[str, Any]],
    notes: str,
    db_path: Path = DB_PATH,
) -> int:
    """Persist a meeting and return its new row id."""
    now = datetime.now(UTC).isoformat()
    with sqlite3.connect(db_path) as conn:
        cursor = conn.execute(
            """
            INSERT INTO meetings
                (user_id, created_at, transcript, summary, tasks, deadlines, notes)
            VALUES (?, ?, ?, ?, ?, ?, ?)
            """,
            (
                user_id,
                now,
                transcript,
                summary,
                json.dumps(tasks, ensure_ascii=False),
                json.dumps(deadlines, ensure_ascii=False),
                notes,
            ),
        )
        conn.commit()
        assert cursor.lastrowid is not None
        return cursor.lastrowid


def get_recent_meetings(
    user_id: int,
    limit: int = 10,
    db_path: Path = DB_PATH,
) -> list[Meeting]:
    """Return the most recent meetings for a user, newest first."""
    with sqlite3.connect(db_path) as conn:
        conn.row_factory = sqlite3.Row
        rows = conn.execute(
            "SELECT * FROM meetings WHERE user_id = ? ORDER BY created_at DESC LIMIT ?",
            (user_id, limit),
        ).fetchall()
    return [_row_to_meeting(row) for row in rows]


def get_meeting(
    meeting_id: int,
    user_id: int,
    db_path: Path = DB_PATH,
) -> Meeting | None:
    """Fetch a single meeting by id, scoped to the owning user."""
    with sqlite3.connect(db_path) as conn:
        conn.row_factory = sqlite3.Row
        row = conn.execute(
            "SELECT * FROM meetings WHERE id = ? AND user_id = ?",
            (meeting_id, user_id),
        ).fetchone()
    return _row_to_meeting(row) if row else None


def _row_to_meeting(row: sqlite3.Row) -> Meeting:
    return Meeting(
        id=row["id"],
        user_id=row["user_id"],
        created_at=datetime.fromisoformat(row["created_at"]),
        transcript=row["transcript"],
        summary=row["summary"],
        tasks=json.loads(row["tasks"]),
        deadlines=json.loads(row["deadlines"]),
        notes=row["notes"],
    )
