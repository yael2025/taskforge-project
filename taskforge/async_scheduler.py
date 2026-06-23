from __future__ import annotations

import asyncio
from typing import Any

from taskforge.task import Task


class AsyncScheduler:
    """Asynchronous task scheduler."""

    def __init__(self, max_concurrency: int = 3) -> None:
        self.max_concurrency = max_concurrency
        self._queue: asyncio.Queue[Task] = asyncio.Queue()
        self._lock = asyncio.Lock()
        self._shutdown_event = asyncio.Event()
        self._results: dict[str, Any] = {}

    async def submit(self, task: Task) -> None:
        """Submit a task to the scheduler."""
        await self._queue.put(task)

    async def cancel(self, task_id: str) -> None:
        """Remove a task result if present."""
        async with self._lock:
            self._results.pop(task_id, None)

    async def run_until_complete(self) -> dict[str, Any]:
        """Execute all queued tasks."""
        semaphore = asyncio.Semaphore(self.max_concurrency)
        workers = []

        while not self._queue.empty():
            task = await self._queue.get()
            workers.append(
                asyncio.create_task(
                    self._execute_task(task, semaphore)
                )
            )

        await asyncio.gather(*workers)

        return self._results

    async def _execute_task(
        self,
        task: Task,
        semaphore: asyncio.Semaphore,
    ) -> None:
        """Execute one task under concurrency control."""
        async with semaphore:
            result = task.payload()

            if asyncio.iscoroutine(result):
                result = await result

            async with self._lock:
                self._results[task.task_id] = result

    async def __aenter__(self) -> AsyncScheduler:
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb) -> None:
        self._shutdown_event.set()