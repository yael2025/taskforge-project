from __future__ import annotations

import asyncio
from typing import Any

from taskforge.exceptions import TaskExecutionError
from taskforge.exceptions import TaskValidationError
from taskforge.task import Task


class AsyncScheduler:
    """Asynchronous scheduler that respects task dependencies."""

    def __init__(self, max_concurrency: int = 3) -> None:
        if max_concurrency <= 0:
            raise ValueError("max_concurrency must be positive")

        self.max_concurrency = max_concurrency
        self._tasks: dict[str, Task] = {}
        self._results: dict[str, Any] = {}
        self._failed: dict[str, BaseException] = {}
        self._cancelled: set[str] = set()

        self._queue: asyncio.Queue[Task] = asyncio.Queue()
        self._lock = asyncio.Lock()
        self._shutdown_event = asyncio.Event()

    async def submit(self, task: Task) -> None:
        """Submit a task to the scheduler."""
        async with self._lock:
            if task.task_id in self._tasks:
                raise TaskValidationError(
                    f"Task already exists: {task.task_id}"
                )

            self._tasks[task.task_id] = task

    async def cancel(self, task_id: str) -> None:
        """Mark a task as cancelled."""
        async with self._lock:
            self._cancelled.add(task_id)

    async def run_until_complete(self) -> dict[str, Any]:
        """Run submitted tasks while respecting dependencies."""
        remaining = set(self._tasks)
        running: set[asyncio.Task[None]] = set()

        while remaining or running:
            ready_tasks = [
                self._tasks[task_id]
                for task_id in remaining
                if self._is_ready(self._tasks[task_id])
            ]

            for task in ready_tasks:
                await self._queue.put(task)

            while (
                not self._queue.empty()
                and len(running) < self.max_concurrency
            ):
                task = await self._queue.get()
                remaining.remove(task.task_id)

                running.add(
                    asyncio.create_task(
                        self._execute_task(task)
                    )
                )

            if running:
                done, running = await asyncio.wait(
                    running,
                    return_when=asyncio.FIRST_COMPLETED,
                )

                for finished_task in done:
                    await finished_task
            elif remaining:
                raise TaskExecutionError(
                    "No runnable tasks remain. Possible failed dependency."
                )

        self._shutdown_event.set()
        return self._results

    def _is_ready(self, task: Task) -> bool:
        """Check whether all dependencies finished successfully."""
        return all(
            dependency_id in self._results
            for dependency_id in task.dependencies
        )

    async def _execute_task(self, task: Task) -> None:
        """Execute a task and store the result or failure."""
        if task.task_id in self._cancelled:
            return

        try:
            result = task.payload()

            if asyncio.iscoroutine(result):
                result = await result

            async with self._lock:
                self._results[task.task_id] = result

        except (RuntimeError, ValueError, TypeError) as error:
            async with self._lock:
                self._failed[task.task_id] = error

            raise TaskExecutionError(
                f"Task failed: {task.task_id}"
            ) from error

    async def __aenter__(self) -> AsyncScheduler:
        """Enter async context manager."""
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb) -> None:
        """Exit async context manager."""
        self._shutdown_event.set()


async def gather_with_limit(
    coros: list[Any],
    limit: int,
) -> list[Any]:
    """Run coroutines with a maximum concurrency limit."""
    if limit <= 0:
        raise ValueError("limit must be positive")

    semaphore = asyncio.Semaphore(limit)

    async def run_one(coro: Any) -> Any:
        async with semaphore:
            return await coro

    return await asyncio.gather(
        *(run_one(coro) for coro in coros)
    )


def run_sync(scheduler: AsyncScheduler) -> dict[str, Any]:
    """
    Run an AsyncScheduler from synchronous code.

    Blocking calls inside async tasks are dangerous because they stop the
    event loop and prevent other tasks from running concurrently.
    """
    return asyncio.run(scheduler.run_until_complete())