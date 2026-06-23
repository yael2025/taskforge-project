from __future__ import annotations

import itertools
import pytest

from taskforge.exceptions import TaskValidationError
from taskforge.task import Task
from taskforge.utils import chunked, retry_values, topological_sort


def dummy_payload() -> None:
    """Dummy payload for test tasks."""
    return None


def test_topological_sort_simple() -> None:
    """Test a basic topological sort with dependent tasks."""
    t1 = Task(task_id="t1", name="Task 1", payload=dummy_payload)
    t2 = Task(
        task_id="t2",
        name="Task 2",
        payload=dummy_payload,
        dependencies=frozenset(["t1"]),
    )
    t3 = Task(
        task_id="t3",
        name="Task 3",
        payload=dummy_payload,
        dependencies=frozenset(["t2"]),
    )

    # Scrambled input order
    sorted_tasks = topological_sort([t3, t1, t2])
    assert sorted_tasks == [t1, t2, t3]


def test_topological_sort_priority_determinism() -> None:
    """Test topological sort's priority-aware determinism.

    When multiple tasks have no unmet dependencies, they must be resolved
    by their priority (higher priority first).
    """
    # t1 and t2 have no dependencies. t2 has higher priority.
    # t3 depends on both.
    t1 = Task(task_id="t1", name="Task 1", payload=dummy_payload, priority=4)
    t2 = Task(task_id="t2", name="Task 2", payload=dummy_payload, priority=8)
    t3 = Task(
        task_id="t3",
        name="Task 3",
        payload=dummy_payload,
        dependencies=frozenset(["t1", "t2"]),
    )

    # Regardless of input permutation, t2 must come before t1 (due to priority)
    # and both must come before t3 (due to dependency).
    for perm in itertools.permutations([t1, t2, t3]):
        sorted_tasks = topological_sort(perm)
        assert sorted_tasks == [t2, t1, t3]


def test_topological_sort_cycle_detection() -> None:
    """Test that circular dependencies raise TaskValidationError."""
    t1 = Task(
        task_id="t1",
        name="Task 1",
        payload=dummy_payload,
        dependencies=frozenset(["t2"]),
    )
    t2 = Task(
        task_id="t2",
        name="Task 2",
        payload=dummy_payload,
        dependencies=frozenset(["t1"]),
    )

    with pytest.raises(TaskValidationError) as excinfo:
        topological_sort([t1, t2])
    assert "Cyclic dependency" in str(excinfo.value)


def test_topological_sort_duplicate_ids() -> None:
    """Test that duplicate task IDs raise TaskValidationError."""
    t1a = Task(task_id="t1", name="Task 1a", payload=dummy_payload)
    t1b = Task(task_id="t1", name="Task 1b", payload=dummy_payload)

    with pytest.raises(TaskValidationError) as excinfo:
        topological_sort([t1a, t1b])
    assert "Duplicate task ID" in str(excinfo.value)


def test_chunked_normal() -> None:
    """Test normal behavior of chunked lazy generator."""
    items = [1, 2, 3, 4, 5, 6, 7, 8]
    gen = chunked(items, 3)

    # It must be a generator
    assert hasattr(gen, "__next__")

    chunks = list(gen)
    assert chunks == [[1, 2, 3], [4, 5, 6], [7, 8]]


def test_chunked_invalid_size() -> None:
    """Test that invalid chunk sizes raise ValueError."""
    with pytest.raises(ValueError) as excinfo:
        list(chunked([1, 2, 3], 0))
    assert "greater than zero" in str(excinfo.value)

    with pytest.raises(ValueError):
        list(chunked([1, 2, 3], -1))


def test_retry_values_normal() -> None:
    """Test retry_values evaluates the function successfully and collects results."""
    counter = 0

    def increment() -> int:
        nonlocal counter
        counter += 1
        return counter

    results = retry_values(increment, attempts=4)
    assert results == [1, 2, 3, 4]
    assert counter == 4


def test_retry_values_with_args() -> None:
    """Test retry_values correctly forwards arguments."""

    def add(x: int, y: int = 10) -> int:
        return x + y

    results = retry_values(add, 3, 5, y=2)
    assert results == [7, 7, 7]


def test_retry_values_invalid_attempts() -> None:
    """Test that negative attempts count raises ValueError."""
    with pytest.raises(ValueError) as excinfo:
        retry_values(lambda: None, -5)
    assert "cannot be negative" in str(excinfo.value)
