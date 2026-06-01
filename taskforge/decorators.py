from __future__ import annotations

import asyncio
import inspect
import logging
import time
from collections.abc import Callable
from functools import wraps
from typing import Any

LOGGER = logging.getLogger(__name__)

def timed(func:Callable[...,Any])-> Callable[...,Any]:
    """Log the execution time of sync or async functions."""

    if inspect.iscoroutinefunction(func):

         @wraps(func)
         async def async_wrapper(*args: Any, **kwargs: Any) -> Any:
            start_time = time.perf_counter()
            result = await func(*args, **kwargs)
            elapsed = time.perf_counter() - start_time
            LOGGER.debug("%s took %.4f seconds", func.__name__, elapsed)
            return result
         return async_wrapper
    
    @wraps(func)
    def sync_wrapper(*args: Any, **kwargs: Any) -> Any:
        start_time = time.perf_counter()
        result = func(*args, **kwargs)
        elapsed = time.perf_counter() - start_time
        LOGGER.debug("%s took %.4f seconds", func.__name__, elapsed)
        return result

    return sync_wrapper

def retry(
    attempts: int,
    exceptions: tuple[type[BaseException], ...],
    backoff: float,
 )-> Callable[[Callable[..., Any]], Callable[..., Any]]:
     """Retry sync or async functions when specific exceptions are raised."""
     if attempts <= 0:
        raise ValueError("attempts must be positive")
     def decorator(func: Callable[..., Any]) -> Callable[..., Any]:
          if inspect.iscoroutinefunction(func):
              @wraps(func)
              async def async_wrapper(*args: Any, **kwargs: Any) -> Any:
                   for attempt in range(1, attempts + 1):
                        try:
                             return await func(*args, **kwargs)
                        except exceptions:
                             if attempt == attempts:
                                raise
                        await asyncio.sleep(backoff)
              return async_wrapper
          
          @wraps(func)
          def sync_wrapper(*args: Any, **kwargs: Any) -> Any:
               for attempt in range(1, attempts + 1):
                    try:
                        return func(*args, **kwargs)
                    except exceptions:
                        if attempt == attempts:
                         raise
                    time.sleep(backoff)

               return sync_wrapper
          return decorator
     
def memoize(func: Callable[..., Any]) -> Callable[..., Any]:
    """Cache function results using a closure-held dictionary."""
    cache: dict[tuple[Any, ...], Any] = {}

    @wraps(func)
    def wrapper(*args: Any, **kwargs: Any) -> Any:
        key = args + tuple(sorted(kwargs.items()))
        if key not in cache:
            cache[key] = func(*args, **kwargs)

        return cache[key]

    def cache_clear() -> None:
            cache.clear()

    def cache_info() -> dict[str, int]:
            return {"size": len(cache)}
    

    wrapper.cache_clear = cache_clear  # type: ignore[attr-defined]
    wrapper.cache_info = cache_info  # type: ignore[attr-defined]

    return wrapper
    
        
        

    
    


               
              

                             
                  
     