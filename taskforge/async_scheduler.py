from __future__ import annotations

import asyncio
from typing import Any

from taskforge.exceptions import TaskExecutionError
from taskforge.exceptions import TaskValidationError
from taskforge.task import Task


PENDING = "PENDING"
RUNNING = "RUNNING"
COMPLETED = "COMPLETED"
FAILED = "FAILED"
CANCELLED = "CANCELLED"


class AsyncScheduler:
    """Asynchronous scheduler that respects dependencies and concurrency limits."""

    def __init__(
        self,
        max_concurrency: int = 3,
        task_timeout: float | None = None,
    ) -> None:
        if max_concurrency <= 0:
            raise ValueError("max_concurrency must be positive")

        self.max_concurrency = max_concurrency
        self.task_timeout = task_timeout

        self._tasks: dict[str, Task] = {}
        self._results: dict[str, Any] = {}
        self._errors: dict[str, BaseException] = {}
        self._status: dict[str, str] = {}

        self._cancelled: set[str] = set()
        self._running_tasks: dict[str, asyncio.Task[None]] = {}

        self._queue: asyncio.Queue[Task] = asyncio.Queue()
        self._lock = asyncio.Lock()
        self._shutdown_event = asyncio.Event()

    async def submit(self, task: Task) -> None:
        """Submit a task to the scheduler."""
        async with self._lock:
            if task.task_id in self._tasks:
                raise TaskValidationError(f"Task already exists: {task.task_id}")

            self._tasks[task.task_id] = task
            self._status[task.task_id] = PENDING

    async def cancel(self, task_id: str) -> None:
        """Cancel a pending or running task."""
        async with self._lock:
            self._cancelled.add(task_id)
            self._status[task_id] = CANCELLED

            running_task = self._running_tasks.get(task_id)
            if running_task is not None:
                running_task.cancel()

    async def run_until_complete(self) -> dict[str, Any]:
        """Run submitted tasks until all tasks complete, fail, or cancel."""
        remaining = set(self._tasks)
        running: set[asyncio.Task[None]] = set()

        while remaining or running:
            self._mark_blocked_tasks_as_failed(remaining)

            ready_tasks = sorted(
                [
                    self._tasks[task_id]
                    for task_id in remaining
                    if self._is_ready(self._tasks[task_id])
                ]
            )

            for task in ready_tasks:
                await self._queue.put(task)

            while not self._queue.empty() and len(running) < self.max_concurrency:
                task = await self._queue.get()

                if task.task_id not in remaining:
                    continue

                remaining.remove(task.task_id)

                if task.task_id in self._cancelled:
                    self._status[task.task_id] = CANCELLED
                    continue

                self._status[task.task_id] = RUNNING
                worker = asyncio.create_task(self._execute_task(task))
                running.add(worker)
                self._running_tasks[task.task_id] = worker

            if running:
                done, running = await asyncio.wait(
                    running,
                    return_when=asyncio.FIRST_COMPLETED,
                )

                for finished_task in done:
                    self._remove_finished_worker(finished_task)

                    try:
                        await finished_task
                    except TaskExecutionError:
                        pass
                    except asyncio.CancelledError:
                        pass

            elif remaining:
                self._mark_remaining_as_failed(remaining)
                break

        self._shutdown_event.set()
        return self._results

    def _is_ready(self, task: Task) -> bool:
        """Return True when all dependencies completed successfully."""
        return all(
            self._status.get(dependency_id) == COMPLETED
            for dependency_id in task.dependencies
        )

    def _mark_blocked_tasks_as_failed(self, remaining: set[str]) -> None:
        """Fail tasks whose dependencies failed or were cancelled."""
        blocked = [
            task_id
            for task_id in remaining
            if any(
                self._status.get(dependency_id) in {FAILED, CANCELLED}
                for dependency_id in self._tasks[task_id].dependencies
            )
        ]

        for task_id in blocked:
            error = TaskExecutionError(f"Dependency failed for task: {task_id}")
            self._errors[task_id] = error
            self._status[task_id] = FAILED
            remaining.remove(task_id)

    def _mark_remaining_as_failed(self, remaining: set[str]) -> None:
        """Fail tasks that cannot run because no progress is possible."""
        for task_id in list(remaining):
            error = TaskExecutionError(f"Task cannot run: {task_id}")
            self._errors[task_id] = error
            self._status[task_id] = FAILED
            remaining.remove(task_id)

    def _remove_finished_worker(self, finished_task: asyncio.Task[None]) -> None:
        """Remove a finished worker from the internal running map."""
        for task_id, worker in list(self._running_tasks.items()):
            if worker is finished_task:
                self._running_tasks.pop(task_id, None)
                break

    async def _execute_task(self, task: Task) -> None:
        """Execute one task and update status dictionaries."""
        if task.task_id in self._cancelled:
            self._status[task.task_id] = CANCELLED
            return

        try:
            result = task.payload()

            if asyncio.iscoroutine(result):
                timeout = task.timeout if task.timeout is not None else self.task_timeout

                if timeout is None:
                    result = await result
                else:
                    result = await asyncio.wait_for(result, timeout=timeout)

            async with self._lock:
                if task.task_id in self._cancelled:
                    self._status[task.task_id] = CANCELLED
                    return

                self._results[task.task_id] = result
                self._status[task.task_id] = COMPLETED

        except TimeoutError as error:
            task_error = TaskExecutionError(f"Task timed out: {task.task_id}")

            async with self._lock:
                self._errors[task.task_id] = task_error
                self._status[task.task_id] = FAILED

            raise task_error from error

        except asyncio.CancelledError:
            async with self._lock:
                self._status[task.task_id] = CANCELLED
            raise

        except BaseException as error:
            task_error = TaskExecutionError(f"Task failed: {task.task_id}")

            async with self._lock:
                self._errors[task.task_id] = task_error
                self._status[task.task_id] = FAILED

            raise task_error from error

    async def __aenter__(self) -> AsyncScheduler:
        """Enter async context manager."""
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb) -> None:
        """Exit async context manager and cancel running tasks."""
        self._shutdown_event.set()

        for task in self._running_tasks.values():
            task.cancel()

        if self._running_tasks:
            await asyncio.gather(
                *self._running_tasks.values(),
                return_exceptions=True,
            )

        self._running_tasks.clear()


async def gather_with_limit(
    coros: list[Any],
    limit: int,
) -> list[Any]:
    """Run coroutines with a maximum concurrency limit and preserve result order."""
    if limit <= 0:
        raise ValueError("limit must be positive")

    results: list[Any] = [None] * len(coros)
    pending = list(enumerate(coros))
    running: set[asyncio.Task[tuple[int, Any]]] = set()

    async def run_one(index: int, coro: Any) -> tuple[int, Any]:
        return index, await coro

    while pending and len(running) < limit:
        index, coro = pending.pop(0)
        running.add(asyncio.create_task(run_one(index, coro)))

    while running:
        done, running = await asyncio.wait(
            running,
            return_when=asyncio.FIRST_COMPLETED,
        )

        for finished in done:
            index, result = await finished
            results[index] = result

            if pending:
                next_index, next_coro = pending.pop(0)
                running.add(asyncio.create_task(run_one(next_index, next_coro)))

    return results


def run_sync(scheduler: AsyncScheduler) -> dict[str, Any]:
    """
    Run an AsyncScheduler from synchronous code.

    Blocking calls inside async tasks are dangerous because they stop the
    event loop and prevent other tasks from running concurrently.
    """
    return asyncio.run(scheduler.run_until_complete())