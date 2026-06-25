"""Unit tests for storage.py (SQLite meeting history)."""

import shutil
import sqlite3
import tempfile
from collections.abc import Generator
from pathlib import Path

import pytest

from storage import Meeting, get_meeting, get_recent_meetings, init_db, save_meeting

# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture()
def db() -> Generator[Path, None, None]:
    """Fresh initialised DB — uses tempfile.mkdtemp to avoid tmp_path Windows cleanup issues."""
    tmpdir = Path(tempfile.mkdtemp(prefix="test_meetings_"))
    path = tmpdir / "test.db"
    init_db(path)
    yield path
    shutil.rmtree(tmpdir, ignore_errors=True)


def _save(db: Path, user_id: int = 1, summary: str = "Test summary", idx: int = 0) -> int:
    return save_meeting(
        user_id=user_id,
        transcript=f"Transcript {idx}",
        summary=summary,
        tasks=[{"owner": "Alice", "task": f"Task {idx}"}],
        deadlines=[{"task": f"Task {idx}", "date": "Friday"}],
        notes="Some notes",
        db_path=db,
    )


# ---------------------------------------------------------------------------
# init_db
# ---------------------------------------------------------------------------


def test_init_db_creates_meetings_table(db: Path) -> None:
    with sqlite3.connect(db) as conn:
        names = [r[0] for r in conn.execute("SELECT name FROM sqlite_master WHERE type='table'")]
    assert "meetings" in names


def test_init_db_is_idempotent(db: Path) -> None:
    """Calling init_db twice must not raise."""
    init_db(db)
    init_db(db)


# ---------------------------------------------------------------------------
# save_meeting
# ---------------------------------------------------------------------------


def test_save_meeting_returns_positive_integer(db: Path) -> None:
    mid = _save(db)
    assert isinstance(mid, int)
    assert mid > 0


def test_save_meeting_increments_id(db: Path) -> None:
    id1 = _save(db, idx=0)
    id2 = _save(db, idx=1)
    assert id2 > id1


def test_save_meeting_persists_all_fields(db: Path) -> None:
    mid = save_meeting(
        user_id=7,
        transcript="Full transcript",
        summary="Full summary",
        tasks=[{"owner": "Bob", "task": "Do thing"}],
        deadlines=[{"task": "Do thing", "date": "Monday"}],
        notes="Important note",
        db_path=db,
    )
    meeting = get_meeting(mid, user_id=7, db_path=db)
    assert meeting is not None
    assert meeting.user_id == 7
    assert meeting.transcript == "Full transcript"
    assert meeting.summary == "Full summary"
    assert meeting.tasks == [{"owner": "Bob", "task": "Do thing"}]
    assert meeting.deadlines == [{"task": "Do thing", "date": "Monday"}]
    assert meeting.notes == "Important note"


def test_save_meeting_preserves_empty_lists(db: Path) -> None:
    mid = save_meeting(
        user_id=1,
        transcript="t",
        summary="s",
        tasks=[],
        deadlines=[],
        notes="",
        db_path=db,
    )
    meeting = get_meeting(mid, user_id=1, db_path=db)
    assert meeting is not None
    assert meeting.tasks == []
    assert meeting.deadlines == []
    assert meeting.notes == ""


# ---------------------------------------------------------------------------
# get_meeting
# ---------------------------------------------------------------------------


def test_get_meeting_returns_none_for_missing_id(db: Path) -> None:
    assert get_meeting(999, user_id=1, db_path=db) is None


def test_get_meeting_returns_none_for_wrong_user(db: Path) -> None:
    mid = _save(db, user_id=1)
    assert get_meeting(mid, user_id=2, db_path=db) is None


def test_get_meeting_returns_meeting_for_correct_user(db: Path) -> None:
    mid = _save(db, user_id=42, summary="My meeting")
    meeting = get_meeting(mid, user_id=42, db_path=db)
    assert isinstance(meeting, Meeting)
    assert meeting.summary == "My meeting"


def test_get_meeting_created_at_is_datetime(db: Path) -> None:
    from datetime import datetime

    mid = _save(db)
    meeting = get_meeting(mid, user_id=1, db_path=db)
    assert meeting is not None
    assert isinstance(meeting.created_at, datetime)


# ---------------------------------------------------------------------------
# get_recent_meetings
# ---------------------------------------------------------------------------


def test_get_recent_meetings_returns_empty_for_new_user(db: Path) -> None:
    assert get_recent_meetings(user_id=999, db_path=db) == []


def test_get_recent_meetings_returns_newest_first(db: Path) -> None:
    for i in range(3):
        _save(db, summary=f"Meeting {i}", idx=i)
    meetings = get_recent_meetings(user_id=1, db_path=db)
    assert len(meetings) == 3
    assert meetings[0].summary == "Meeting 2"
    assert meetings[2].summary == "Meeting 0"


def test_get_recent_meetings_respects_limit(db: Path) -> None:
    for i in range(5):
        _save(db, idx=i)
    meetings = get_recent_meetings(user_id=1, limit=3, db_path=db)
    assert len(meetings) == 3


def test_get_recent_meetings_isolates_users(db: Path) -> None:
    _save(db, user_id=1, summary="User 1 meeting")
    _save(db, user_id=2, summary="User 2 meeting")
    meetings = get_recent_meetings(user_id=1, db_path=db)
    assert len(meetings) == 1
    assert meetings[0].summary == "User 1 meeting"


def test_get_recent_meetings_default_limit_is_10(db: Path) -> None:
    for i in range(15):
        _save(db, idx=i)
    meetings = get_recent_meetings(user_id=1, db_path=db)
    assert len(meetings) == 10
