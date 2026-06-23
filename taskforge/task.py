from __future__ import annotations

import inspect
from dataclasses import dataclass
from dataclasses import field
from datetime import datetime
from typing import Any
from typing import Callable
from typing import Coroutine

from taskforge.exceptions import TaskValidationError


@dataclass(order=True, frozen=True)
class Task:
    """Represents a scheduled task."""

    sort_index: tuple[int, datetime, str] = field(init=False, repr=False)

    task_id: str = field(compare=False)
    name: str = field(compare=False)
    priority: int = field(default=5, compare=False)
    dependencies: frozenset[str] = field(default_factory=frozenset, compare=False)
    payload: Callable[..., Any] | Coroutine[Any, Any, Any] = field(
        default=None,
        compare=False,
    )
    created_at: datetime = field(default_factory=datetime.now, compare=False)

    def __post_init__(self) -> None:
        """Validate task fields after initialization."""
        if not isinstance(self.task_id, str) or not self.task_id.strip():
            raise TaskValidationError("task_id cannot be empty")

        if not isinstance(self.name, str) or not self.name.strip():
            raise TaskValidationError("name cannot be empty")

        if not isinstance(self.priority, int) or not 1 <= self.priority <= 10:
            raise TaskValidationError("priority must be between 1 and 10")

        if not isinstance(self.dependencies, frozenset):
            raise TaskValidationError("dependencies must be a frozenset")

        if not all(isinstance(dep, str) for dep in self.dependencies):
            raise TaskValidationError("dependencies must contain only strings")

        if self.payload is None:
            raise TaskValidationError("payload is required")

        if not callable(self.payload) and not inspect.iscoroutine(self.payload):
            raise TaskValidationError("payload must be callable or coroutine")

        object.__setattr__(
            self,
            "sort_index",
            (-self.priority, self.created_at, self.task_id),
        )

    def __eq__(self, other: object) -> bool:
        """Compare tasks by task_id."""
        if not isinstance(other, Task):
            return NotImplemented

        return self.task_id == other.task_id

    def __hash__(self) -> int:
        """Hash task by task_id."""
        return hash(self.task_id)