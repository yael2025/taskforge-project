from __future__ import annotations

import heapq
from collections.abc import Callable
from collections.abc import Generator
from collections.abc import Iterable
from typing import Any

from taskforge.utils import chunked

def task_batches(tasks: Iterable[Any], batch_size: int)-> Generator[list[Any], None, None]:
     """Yield task batches with the requested batch size."""
     yield from chunked(tasks, batch_size)

def merge_sorted_streams(
    *iterables: Iterable[Any],
    key: Callable[[Any], Any]| None = None,
    )-> Iterable[Any]:
      """Merge sorted iterables lazily."""
      yield from heapq.merge(*iterables, key=key)

def paginate(
    query_fn: Callable[[int, int], list[Any]],
    page_size: int,
) -> Generator[Any, None, None]:
    """Yield items page by page until the query returns an empty list."""
    if page_size <= 0:
        raise ValueError("page_size must be positive")

    offset = 0

    while page := query_fn(offset, page_size):
        yield from page
        offset += page_size

def event_router()-> Generator[None, dict[str, Any], None]:
     """Route incoming events to registered handlers."""
     handlers : dict[str, Callable[[dict[str, Any]], None]]={}

     try:
          while True:
               event = yield

               if event is None:
                    continue
               
               event_type = event.get("type")
               if event_type == "register":
                    name = event["name"]
                    handler = event["handler"]
                    handlers[name] = handler
                    continue
               if event_type in handlers:
                    handlers[event_type](event)

     finally:
          handlers.clear()
          

     