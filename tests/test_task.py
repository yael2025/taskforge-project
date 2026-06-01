from datetime import datetime

import pytest

from taskforge.exceptions import TaskValidationError
from taskforge.task import Task


def dummy_function() -> str:
    return "ok"


def test_create_valid_task() -> None:

    task = Task(
        task_id="task-1",
        name="Test Task",
        priority=5,
        payload=dummy_function,
    )

    assert task.task_id == "task-1"


def test_empty_task_id_raises() -> None:

    with pytest.raises(TaskValidationError):
        Task(
            task_id="",
            name="Test Task",
            payload=dummy_function,
        )


def test_empty_name_raises() -> None:

    with pytest.raises(TaskValidationError):
        Task(
            task_id="task-1",
            name="",
            payload=dummy_function,
        )


def test_invalid_priority_raises() -> None:

    with pytest.raises(TaskValidationError):
        Task(
            task_id="task-1",
            name="Test Task",
            priority=20,
            payload=dummy_function,
        )


def test_created_at_is_datetime() -> None:

    task = Task(
        task_id="task-1",
        name="Test Task",
        payload=dummy_function,
    )

    assert isinstance(task.created_at, datetime)