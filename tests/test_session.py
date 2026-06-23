from __future__ import annotations

import logging
import sqlite3

import pytest

from taskforge.exceptions import SchedulerStateError
from taskforge.session import SchedulerSession
from taskforge.session import timed_block


def test_scheduler_session_commits_on_success(tmp_path) -> None:
    """Test that SchedulerSession commits on clean exit."""
    db_path = tmp_path / "test.db"

    with SchedulerSession(db_path) as conn:
        conn.execute("CREATE TABLE items (id INTEGER PRIMARY KEY, name TEXT)")
        conn.execute("INSERT INTO items (name) VALUES (?)", ("apple",))

    with sqlite3.connect(db_path) as conn:
        result = conn.execute("SELECT name FROM items").fetchone()

    assert result == ("apple",)


def test_scheduler_session_rolls_back_on_exception(tmp_path) -> None:
    """Test that SchedulerSession rolls back when an exception occurs."""
    db_path = tmp_path / "test.db"

    with sqlite3.connect(db_path) as conn:
        conn.execute("CREATE TABLE items (id INTEGER PRIMARY KEY, name TEXT)")

    with pytest.raises(RuntimeError):
        with SchedulerSession(db_path) as conn:
            conn.execute("INSERT INTO items (name) VALUES (?)", ("apple",))
            raise RuntimeError("boom")

    with sqlite3.connect(db_path) as conn:
        result = conn.execute("SELECT COUNT(*) FROM items").fetchone()

    assert result == (0,)


def test_scheduler_session_reentrant_safe(tmp_path) -> None:
    """Test that entering the same session twice raises SchedulerStateError."""
    db_path = tmp_path / "test.db"
    session = SchedulerSession(db_path)

    with session:
        with pytest.raises(SchedulerStateError):
            with session:
                pass


def test_timed_block_logs_elapsed_time(caplog) -> None:
    """Test that timed_block logs elapsed time."""
    caplog.set_level(logging.INFO)

    with timed_block("unit-test-block"):
        pass

    records = [record for record in caplog.records if record.name == "taskforge.session"]

    assert len(records) == 1
    assert "unit-test-block" in records[0].message
    assert "took" in records[0].message