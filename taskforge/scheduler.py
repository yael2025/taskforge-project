from __future__ import annotations

from collections.abc import Iterator

from taskforge.task import Task
from taskforge.utils import topological_sort


class Scheduler:
    """Manage pending tasks and expose a simple Pythonic API."""

    def __init__(self) -> None:
        self._tasks: dict[str,Task] = {}

    def submit(self, task: Task) -> None:
        """Add a task to the scheduler."""
        self._tasks[task.task_id] = task

    def __len__(self) -> int:
        """Return the number of pending tasks."""
        return len(self._tasks)
    
    def __contains__(self, task_id: str) -> bool:
        """Check whether a task id exists in the scheduler."""
        return task_id in self._tasks
    
    def __iter__(self) -> Iterator[Task]:
        """Yield ready tasks ordered by dependencies and priority."""
        yield from topological_sort(self._tasks.values())

    def __iadd__(self, task: Task) -> Scheduler:
        """Add a task using the += operator."""
        self.submit(task)
        return self