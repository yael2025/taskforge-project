from __future__ import annotations

import asyncio
from datetime import datetime
import pytest

from taskforge.async_scheduler import AsyncScheduler, gather_with_limit, run_sync
from taskforge.exceptions import SchedulerStateError, TaskExecutionError
from taskforge.task import Task


def dummy_sync() -> str:
    """Synchronous test payload."""
    return "sync"


async def dummy_async() -> str:
    """Asynchronous test payload."""
    await asyncio.sleep(0.001)
    return "async"


def test_async_scheduler_simple() -> None:
    """Test basic submission and complete run of independent tasks."""
    scheduler = AsyncScheduler()

    t1 = Task(task_id="t1", name="Task 1", payload=dummy_sync)
    t2 = Task(task_id="t2", name="Task 2", payload=dummy_async)

    async def main() -> None:
        async with scheduler as s:
            await s.submit(t1)
            await s.submit(t2)
            await s.run_until_complete()

    asyncio.run(main())

    assert scheduler._status["t1"] == "COMPLETED"
    assert scheduler._status["t2"] == "COMPLETED"
    assert scheduler._results["t1"] == "sync"
    assert scheduler._results["t2"] == "async"


def test_async_scheduler_dependencies() -> None:
    """Test that task dependencies are respected and run in correct sequence."""
    order: list[str] = []

    async def payload_a() -> None:
        order.append("A")

    async def payload_b() -> None:
        order.append("B")

    async def payload_c() -> None:
        order.append("C")

    # C depends on B, which depends on A
    t_a = Task(task_id="A", name="Task A", payload=payload_a)
    t_b = Task(task_id="B", name="Task B", payload=payload_b, dependencies=frozenset(["A"]))
    t_c = Task(task_id="C", name="Task C", payload=payload_c, dependencies=frozenset(["B"]))

    async def main() -> None:
        async with AsyncScheduler() as s:
            await s.submit(t_c)
            await s.submit(t_a)
            await s.submit(t_b)
            await s.run_until_complete()

    asyncio.run(main())
    assert order == ["A", "B", "C"]


def test_async_scheduler_dependency_failure() -> None:
    """Test that if a dependency fails, dependent tasks are marked as FAILED."""

    async def bad_payload() -> None:
        raise ValueError("Boom")

    async def good_payload() -> None:
        pass

    t_bad = Task(task_id="bad", name="Bad Task", payload=bad_payload)
    t_good = Task(task_id="good", name="Good Task", payload=good_payload, dependencies=frozenset(["bad"]))

    scheduler = AsyncScheduler()

    async def main() -> None:
        async with scheduler as s:
            await s.submit(t_bad)
            await s.submit(t_good)
            await s.run_until_complete()

    asyncio.run(main())
    assert scheduler._status["bad"] == "FAILED"
    assert scheduler._status["good"] == "FAILED"


def test_async_scheduler_concurrency_limit() -> None:
    """Test that max_concurrency limit is strictly honored."""
    active_count = 0
    max_observed = 0
    lock = asyncio.Lock()

    async def throttled_payload() -> None:
        nonlocal active_count, max_observed
        async with lock:
            active_count += 1
            if active_count > max_observed:
                max_observed = active_count

        await asyncio.sleep(0.01)

        async with lock:
            active_count -= 1

    t1 = Task(task_id="t1", name="T1", payload=throttled_payload)
    t2 = Task(task_id="t2", name="T2", payload=throttled_payload)
    t3 = Task(task_id="t3", name="T3", payload=throttled_payload)
    t4 = Task(task_id="t4", name="T4", payload=throttled_payload)

    async def main() -> None:
        # Max concurrency: 2
        async with AsyncScheduler(max_concurrency=2) as s:
            await s.submit(t1)
            await s.submit(t2)
            await s.submit(t3)
            await s.submit(t4)
            await s.run_until_complete()

    asyncio.run(main())
    assert max_observed <= 2
    assert max_observed > 0


def test_async_scheduler_timeouts() -> None:
    """Test task execution timeouts transition task to FAILED with error cause."""

    async def slow_payload() -> None:
        await asyncio.sleep(0.1)

    # Task timeout is 0.01s (exceeded by slow_payload of 0.1s)
    t_slow = Task(task_id="slow", name="Slow Task", payload=slow_payload, timeout=0.01)

    async def main() -> None:
        async with AsyncScheduler() as s:
            await s.submit(t_slow)
            await s.run_until_complete()

    scheduler = AsyncScheduler()

    async def run_sched() -> None:
        async with scheduler as s:
            await s.submit(t_slow)
            await s.run_until_complete()

    asyncio.run(run_sched())
    assert scheduler._status["slow"] == "FAILED"
    assert isinstance(scheduler._errors["slow"], TaskExecutionError)
    assert "timed out" in str(scheduler._errors["slow"])


def test_async_scheduler_cancellation() -> None:
    """Test dynamic task cancellation before or during execution."""

    async def slow_payload() -> None:
        await asyncio.sleep(0.1)

    t_cancel = Task(task_id="t_cancel", name="Cancel Task", payload=slow_payload)

    async def main() -> None:
        scheduler = AsyncScheduler()
        async with scheduler as s:
            await s.submit(t_cancel)

            # Start complete loop in background
            run_task = asyncio.create_task(s.run_until_complete())
            await asyncio.sleep(0.005)  # wait for worker to pull and run

            # Cancel it dynamically
            await s.cancel("t_cancel")
            await run_task
            assert scheduler._status["t_cancel"] == "CANCELLED"

    asyncio.run(main())


def test_gather_with_limit() -> None:
    """Test gather_with_limit concurrency throttling and submission ordering."""
    order: list[int] = []

    async def work(idx: int, delay: float) -> int:
        await asyncio.sleep(delay)
        order.append(idx)
        return idx

    async def main() -> None:
        # Submission order: work(0), work(1), work(2)
        # Even if work(1) finishes first, gather returns them in exact submission order [0, 1, 2]
        coros = [work(0, 0.02), work(1, 0.001), work(2, 0.01)]
        results = await gather_with_limit(coros, limit=2)
        assert results == [0, 1, 2]
        # Actual execution completion sequence: index 1 first, then 2, then 0
        assert sorted(order) == [0, 1, 2]
        assert order[0] == 1

    asyncio.run(main())


def test_run_sync_bridge() -> None:
    """Test synchronous convenience run_sync wraps asyncio.run correctly."""
    scheduler = AsyncScheduler()
    t = Task(task_id="t_sync", name="Bridge Task", payload=dummy_sync)

    async def prepare() -> None:
        await scheduler.submit(t)

    asyncio.run(prepare())

    # Executes blocking run_sync
    run_sync(scheduler)
    assert scheduler._status["t_sync"] == "COMPLETED"
    assert scheduler._results["t_sync"] == "sync"
