from __future__ import annotations

import asyncio
from datetime import datetime, timedelta
import pytest

from taskforge.exceptions import TaskValidationError
from taskforge.task import Task


def dummy_sync_payload() -> str:
    """A dummy synchronous task payload."""
    return "sync_result"


async def dummy_async_payload() -> str:
    """A dummy asynchronous task payload."""
    return "async_result"


def test_task_creation_valid() -> None:
    """Test creating a Task with valid parameters."""
    task = Task(
        task_id="task-1",
        name="Test Task",
        payload=dummy_sync_payload,
        priority=8,
        dependencies=frozenset(["dep-1", "dep-2"]),
    )
    assert task.task_id == "task-1"
    assert task.name == "Test Task"
    assert task.payload() == "sync_result"
    assert task.priority == 8
    assert task.dependencies == frozenset(["dep-1", "dep-2"])
    assert isinstance(task.created_at, datetime)


def test_task_creation_defaults() -> None:
    """Test default values of the Task dataclass."""
    task = Task(
        task_id="task-default",
        name="Default Task",
        payload=dummy_async_payload,
    )
    assert task.priority == 5
    assert task.dependencies == frozenset()
    assert isinstance(task.created_at, datetime)


def test_task_validation_empty_id() -> None:
    """Test that TaskValidationError is raised for empty task_id."""
    with pytest.raises(TaskValidationError) as excinfo:
        Task(task_id="", name="Invalid", payload=dummy_sync_payload)
    assert "task_id cannot be empty" in str(excinfo.value)

    with pytest.raises(TaskValidationError):
        Task(task_id="   ", name="Invalid", payload=dummy_sync_payload)


def test_task_validation_bad_id_type() -> None:
    """Test that TaskValidationError is raised for non-string task_id."""
    with pytest.raises(TaskValidationError):
        Task(task_id=123, name="Invalid", payload=dummy_sync_payload)  # type: ignore[arg-type]


def test_task_validation_bad_name_type() -> None:
    """Test that TaskValidationError is raised for non-string name."""
    with pytest.raises(TaskValidationError):
        Task(task_id="t1", name=None, payload=dummy_sync_payload)  # type: ignore[arg-type]


def test_task_validation_priority_bounds() -> None:
    """Test that priority must be in range 1 to 10."""
    with pytest.raises(TaskValidationError):
        Task(task_id="t1", name="p0", payload=dummy_sync_payload, priority=0)

    with pytest.raises(TaskValidationError):
        Task(task_id="t1", name="p11", payload=dummy_sync_payload, priority=11)

    with pytest.raises(TaskValidationError):
        Task(task_id="t1", name="p-bad", payload=dummy_sync_payload, priority="5")  # type: ignore[arg-type]


def test_task_validation_bad_dependencies() -> None:
    """Test that dependencies must be a frozenset of strings."""
    with pytest.raises(TaskValidationError):
        Task(task_id="t1", name="d-list", payload=dummy_sync_payload, dependencies=["dep"])  # type: ignore[arg-type]

    with pytest.raises(TaskValidationError):
        Task(
            task_id="t1",
            name="d-num",
            payload=dummy_sync_payload,
            dependencies=frozenset([123]),  # type: ignore[arg-type]
        )


def test_task_validation_bad_payload() -> None:
    """Test that payload must be a callable or coroutine."""
    with pytest.raises(TaskValidationError):
        Task(task_id="t1", name="no-payload", payload=None)  # type: ignore[arg-type]

    with pytest.raises(TaskValidationError):
        Task(task_id="t1", name="no-payload-str", payload="not callable")  # type: ignore[arg-type]


def test_task_equality_and_hash() -> None:
    """Test equality and hashing based strictly on task_id."""
    t1 = Task(task_id="same-id", name="Task 1", payload=dummy_sync_payload, priority=3)
    t2 = Task(task_id="same-id", name="Task 2", payload=dummy_sync_payload, priority=9)
    t3 = Task(task_id="diff-id", name="Task 1", payload=dummy_sync_payload, priority=3)

    assert t1 == t2
    assert t1 != t3
    assert hash(t1) == hash(t2)
    assert hash(t1) != hash(t3)


def test_task_ordering() -> None:
    """Test priority and created_at sorting order of tasks.

    Higher priority comes first (descending).
    Older created_at comes first (ascending).
    Lexicographical task_id comes first as tie-breaker (ascending).
    """
    now = datetime.now()
    # High priority, created later
    t_high = Task(
        task_id="t-high",
        name="High Priority",
        payload=dummy_sync_payload,
        priority=9,
        created_at=now + timedelta(seconds=10),
    )
    # Low priority, created earlier
    t_low = Task(
        task_id="t-low",
        name="Low Priority",
        payload=dummy_sync_payload,
        priority=3,
        created_at=now,
    )
    # Medium priority, older
    t_med_old = Task(
        task_id="t-med-old",
        name="Medium Old",
        payload=dummy_sync_payload,
        priority=6,
        created_at=now,
    )
    # Medium priority, newer
    t_med_new = Task(
        task_id="t-med-new",
        name="Medium New",
        payload=dummy_sync_payload,
        priority=6,
        created_at=now + timedelta(seconds=5),
    )
    # Medium priority, same age, tie breaker
    t_med_tie = Task(
        task_id="t-med-tie",
        name="Medium Old Tie Breaker",
        payload=dummy_sync_payload,
        priority=6,
        created_at=now,
    )

    # Ascending sort (standard list.sort or sorted()) will put the "lesser" Tasks first.
    # High priority is "less than" low priority in order (since it comes first).
    # So t_high < t_med_old < t_med_new < t_low
    assert t_high < t_med_old
    assert t_med_old < t_med_new
    assert t_med_old < t_med_tie  # t-med-old < t-med-tie because "old" comes before "tie"

    sorted_tasks = sorted([t_low, t_high, t_med_new, t_med_old, t_med_tie])
    expected_order = [t_high, t_med_old, t_med_tie, t_med_new, t_low]
    assert sorted_tasks == expected_order
