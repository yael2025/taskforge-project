from __future__ import annotations

class TaskForgeError(Exception):
    """Base exception for all TaskForge errors."""


class TaskValidationError(TaskForgeError):
    """Raised when a task has invalid data."""


class TaskExecutionError(TaskForgeError):
     """Raised when a task fails during execution."""

class SchedulerStateError(TaskForgeError):
    """Raised when the scheduler is in an invalid state."""


    