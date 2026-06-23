from __future__ import annotations

import pytest

from taskforge.executors import AsyncExecutor
from taskforge.executors import BaseExecutor
from taskforge.executors import SyncExecutor
from taskforge.executors import ThreadPoolExecutorBackend
from taskforge.task import Task


def sync_payload() -> str:
    """Return a sync result."""
    return "sync result"


async def async_payload() -> str:
    """Return an async result."""
    return "async result"


def test_base_executor_cannot_be_instantiated() -> None:
    """Test that BaseExecutor is abstract."""
    with pytest.raises(TypeError):
        BaseExecutor()


def test_sync_executor_runs_task() -> None:
    """Test SyncExecutor runs synchronous payloads."""
    task = Task(
        task_id="sync",
        name="Sync task",
        payload=sync_payload,
    )

    result = SyncExecutor().run(task)

    assert result == "sync result"


def test_thread_pool_executor_backend_runs_task() -> None:
    """Test ThreadPoolExecutorBackend runs synchronous payloads."""
    task = Task(
        task_id="thread",
        name="Thread task",
        payload=sync_payload,
    )

    result = ThreadPoolExecutorBackend(max_workers=1).run(task)

    assert result == "sync result"


def test_async_executor_runs_async_task() -> None:
    """Test AsyncExecutor runs asynchronous payloads."""
    task = Task(
        task_id="async",
        name="Async task",
        payload=async_payload,
    )

    result = AsyncExecutor().run(task)

    assert result == "async result"


def test_async_executor_returns_sync_result() -> None:
    """Test AsyncExecutor also supports sync payload results."""
    task = Task(
        task_id="sync-in-async",
        name="Sync in async executor",
        payload=sync_payload,
    )

    result = AsyncExecutor().run(task)

    assert result == "sync result"