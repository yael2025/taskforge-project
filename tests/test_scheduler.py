from __future__ import annotations

from taskforge.scheduler import Scheduler
from taskforge.task import Task


def dummy_payload() -> str:
    """Return a dummy result."""
    return "ok"


def test_scheduler_submit_and_len() -> None:
    """Test submitting tasks and pending count."""
    scheduler = Scheduler()

    task = Task(
        task_id="task-1",
        name="Task 1",
        payload=dummy_payload,
    )

    scheduler.submit(task)

    assert len(scheduler) == 1


def test_scheduler_contains() -> None:
    """Test task id membership."""
    scheduler = Scheduler()

    task = Task(
        task_id="task-1",
        name="Task 1",
        payload=dummy_payload,
    )

    scheduler.submit(task)

    assert "task-1" in scheduler
    assert "missing" not in scheduler


def test_scheduler_iadd() -> None:
    """Test adding a task using +=."""
    scheduler = Scheduler()

    task = Task(
        task_id="task-1",
        name="Task 1",
        payload=dummy_payload,
    )

    scheduler += task

    assert len(scheduler) == 1
    assert "task-1" in scheduler


def test_scheduler_iteration_respects_priority() -> None:
    """Test scheduler iteration returns tasks by priority."""
    scheduler = Scheduler()

    low = Task(
        task_id="low",
        name="Low",
        priority=2,
        payload=dummy_payload,
    )

    high = Task(
        task_id="high",
        name="High",
        priority=9,
        payload=dummy_payload,
    )

    scheduler += low
    scheduler += high

    result = list(scheduler)

    assert result == [high, low]


def test_scheduler_iteration_respects_dependencies() -> None:
    """Test scheduler iteration respects task dependencies."""
    scheduler = Scheduler()

    first = Task(
        task_id="first",
        name="First",
        payload=dummy_payload,
    )

    second = Task(
        task_id="second",
        name="Second",
        dependencies=frozenset({"first"}),
        payload=dummy_payload,
    )

    scheduler += second
    scheduler += first

    result = list(scheduler)

    assert result == [first, second]