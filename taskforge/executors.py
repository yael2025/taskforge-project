from __future__ import annotations

import asyncio
from abc import ABC
from abc import abstractmethod
from concurrent.futures import ThreadPoolExecutor
from typing import Any

from taskforge.task import Task

class BaseExecutor(ABC):
    """Abstract base class for all task executors."""

    @abstractmethod
    def run(self, task:Task)-> Any:
        """Run a task and return its result."""

class SyncExecutor(BaseExecutor):
    """Execute a task synchronously in the current thread."""

    def run(self, task: Task)-> Any:
       """Run a synchronous task payload."""
       return task.payload()

class ThreadPoolExecutorBackend(BaseExecutor):
    """Execute a synchronous task inside a thread pool."""

    def __init__(self, max_workers: int | None = None)-> None:
        self.max_workers = max_workers

    def run(self, task: Task) -> Any:
        """Run a task payload using ThreadPoolExecutor."""
        with ThreadPoolExecutor(max_workers=self.max_workers) as executor:
            future = executor.submit(task.payload)
            return future.result()
        
class AsyncExecutor(BaseExecutor):
    """Execute an async task payload."""

    def run(self, task:Task)->Any:
        """Run an async task payload using asyncio.run."""
        payload_result = task.payload()

        if asyncio.iscoroutine(payload_result):
            return asyncio.run(payload_result)
        
        return payload_result