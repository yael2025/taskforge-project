from __future__ import annotations

from collections.abc import Callable
from collections.abc import Iterable
from itertools import islice
from typing import Any

from taskforge.exceptions import TaskValidationError
from taskforge.task import Task


def chunked(iterable: Iterable[Any], size: int) -> Iterable[list[Any]]:
    """Yield lists of the given size from an iterable."""
    if size <= 0:
        raise ValueError("size must be greater than zero")

    iterator = iter(iterable)

    while chunk := list(islice(iterator, size)):
        yield chunk


def retry_values(
    func: Callable[..., Any],
    attempts: int,
    *args: Any,
    **kwargs: Any,
) -> list[Any]:
    """Call a function several times and return all results."""
    if attempts < 0:
        raise ValueError("attempts cannot be negative")

    if attempts == 0:
        return []

    return [func(*args, **kwargs) for _ in range(attempts)]


def topological_sort(tasks: Iterable[Task]) -> list[Task]:
    """Sort tasks according to their dependencies."""
    task_list = list(tasks)
    task_ids = [task.task_id for task in task_list]

    if len(task_ids) != len(set(task_ids)):
        raise TaskValidationError("Duplicate task ID found")

    task_map = {task.task_id: task for task in task_list}
    visited: set[str] = set()
    visiting: set[str] = set()
    result: list[Task] = []

    def visit(task: Task) -> None:
        if task.task_id in visited:
            return

        if task.task_id in visiting:
            raise TaskValidationError("Cyclic dependency detected")

        visiting.add(task.task_id)

        for dependency_id in sorted(task.dependencies):
            if dependency_id not in task_map:
                raise TaskValidationError(
                    f"missing dependency: {dependency_id}"
                )

            visit(task_map[dependency_id])

        visiting.remove(task.task_id)
        visited.add(task.task_id)
        result.append(task)

    for task in sorted(task_map.values()):
        visit(task)

    return result