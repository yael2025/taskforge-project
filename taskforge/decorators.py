from __future__ import annotations

import asyncio
import inspect
import logging
import time
from collections import namedtuple
from collections.abc import Callable
from functools import wraps
from types import NoneType
from types import UnionType
from typing import Any
from typing import get_args
from typing import get_origin
from typing import get_type_hints


LOGGER = logging.getLogger(__name__)
CacheInfo = namedtuple("CacheInfo", ["hits", "misses", "currsize"])


def timed(func: Callable[..., Any]) -> Callable[..., Any]:
    """Log the execution time of sync or async functions."""

    if inspect.iscoroutinefunction(func):

        @wraps(func)
        async def async_wrapper(*args: Any, **kwargs: Any) -> Any:
            start_time = time.perf_counter()
            result = await func(*args, **kwargs)
            elapsed = time.perf_counter() - start_time
            LOGGER.debug("%s executed in %.4f seconds", func.__name__, elapsed)
            return result

        return async_wrapper

    @wraps(func)
    def sync_wrapper(*args: Any, **kwargs: Any) -> Any:
        start_time = time.perf_counter()
        result = func(*args, **kwargs)
        elapsed = time.perf_counter() - start_time
        LOGGER.debug("%s executed in %.4f seconds", func.__name__, elapsed)
        return result

    return sync_wrapper


def retry(
    attempts: int,
    exceptions: type[BaseException] | tuple[type[BaseException], ...],
    backoff: float,
) -> Callable[[Callable[..., Any]], Callable[..., Any]]:
    """Retry sync or async functions when specific exceptions are raised."""
    if attempts <= 0:
        raise ValueError("attempts must be positive")

    if not isinstance(exceptions, tuple):
        exceptions = (exceptions,)

    if not all(issubclass(error, BaseException) for error in exceptions):
        raise ValueError("exceptions must contain exception types")

    if backoff < 0:
        raise ValueError("backoff cannot be negative")

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


def _make_cache_key(args: tuple[Any, ...], kwargs: dict[str, Any]) -> tuple[Any, ...]:
    """Create a hashable cache key from args and kwargs."""
    return args + tuple(sorted(kwargs.items()))


def memoize(func: Callable[..., Any]) -> Callable[..., Any]:
    """Cache function results using a closure-held dictionary."""
    cache: dict[tuple[Any, ...], Any] = {}
    hits = 0
    misses = 0

    if inspect.iscoroutinefunction(func):

        @wraps(func)
        async def async_wrapper(*args: Any, **kwargs: Any) -> Any:
            nonlocal hits, misses
            key = _make_cache_key(args, kwargs)

            if key in cache:
                hits += 1
                return cache[key]

            misses += 1
            result = await func(*args, **kwargs)
            cache[key] = result
            return result

        def cache_clear() -> None:
            nonlocal hits, misses
            cache.clear()
            hits = 0
            misses = 0

        def cache_info() -> CacheInfo:
            return CacheInfo(hits, misses, len(cache))

        async_wrapper.cache_clear = cache_clear  # type: ignore[attr-defined]
        async_wrapper.cache_info = cache_info  # type: ignore[attr-defined]
        return async_wrapper

    @wraps(func)
    def sync_wrapper(*args: Any, **kwargs: Any) -> Any:
        nonlocal hits, misses
        key = _make_cache_key(args, kwargs)

        if key in cache:
            hits += 1
            return cache[key]

        misses += 1
        result = func(*args, **kwargs)
        cache[key] = result
        return result

    def cache_clear() -> None:
        nonlocal hits, misses
        cache.clear()
        hits = 0
        misses = 0

    def cache_info() -> CacheInfo:
        return CacheInfo(hits, misses, len(cache))

    sync_wrapper.cache_clear = cache_clear  # type: ignore[attr-defined]
    sync_wrapper.cache_info = cache_info  # type: ignore[attr-defined]
    return sync_wrapper


def _matches_type(value: Any, expected_type: Any) -> bool:
    """Check whether a value matches a supported type hint."""
    origin = get_origin(expected_type)
    args = get_args(expected_type)

    if expected_type is Any:
        return True

    if expected_type is None or expected_type is NoneType:
        return value is None

    if origin in (UnionType, None) and isinstance(expected_type, UnionType):
        return any(_matches_type(value, arg) for arg in args)

    if str(origin) == "typing.Union":
        return any(_matches_type(value, arg) for arg in args)

    if origin is list:
        return isinstance(value, list) and all(
            _matches_type(item, args[0]) for item in value
        )

    if origin is dict:
        key_type, value_type = args
        return isinstance(value, dict) and all(
            _matches_type(key, key_type) and _matches_type(val, value_type)
            for key, val in value.items()
        )

    if origin is set:
        return isinstance(value, set) and all(
            _matches_type(item, args[0]) for item in value
        )

    if origin is tuple:
        return isinstance(value, tuple)

    if origin is not None:
        return isinstance(value, origin)

    return isinstance(value, expected_type)


def validate_types(func: Callable[..., Any]) -> Callable[..., Any]:
    """Validate function arguments according to their type hints."""
    hints = get_type_hints(func)
    signature = inspect.signature(func)

    @wraps(func)
    def wrapper(*args: Any, **kwargs: Any) -> Any:
        bound_arguments = signature.bind(*args, **kwargs)
        bound_arguments.apply_defaults()

        for name, value in bound_arguments.arguments.items():
            if name not in hints:
                continue

            parameter = signature.parameters[name]
            expected_type = hints[name]

            if parameter.kind is inspect.Parameter.VAR_POSITIONAL:
                if not all(_matches_type(item, expected_type) for item in value):
                    raise TypeError(
                        f"Argument '{name}' must be of type {expected_type}"
                    )
                continue

            if parameter.kind is inspect.Parameter.VAR_KEYWORD:
                if not all(_matches_type(item, expected_type) for item in value.values()):
                    raise TypeError(
                        f"Argument '{name}' must be of type {expected_type}"
                    )
                continue

            if not _matches_type(value, expected_type):
                raise TypeError(
                    f"Argument '{name}' must be of type {expected_type}"
                )

        return func(*args, **kwargs)

    return wrapper