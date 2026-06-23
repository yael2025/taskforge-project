from __future__ import annotations

import asyncio
import logging
import time
import pytest

from taskforge.decorators import memoize, retry, timed, validate_types


# =====================================================================
# 1. Tests for @timed
# =====================================================================

def test_timed_sync(caplog: pytest.LogCaptureFixture) -> None:
    """Test that @timed logs synchronous execution time at DEBUG level."""
    caplog.set_level(logging.DEBUG)

    @timed
    def slow_sync(x: int) -> int:
        time.sleep(0.01)
        return x * 2

    res = slow_sync(5)
    assert res == 10
    # Filter to only get records from taskforge.decorators
    decorator_records = [r for r in caplog.records if r.name == "taskforge.decorators"]
    assert len(decorator_records) == 1
    assert decorator_records[0].levelno == logging.DEBUG
    assert "slow_sync" in decorator_records[0].message
    assert "executed in" in decorator_records[0].message


def test_timed_async(caplog: pytest.LogCaptureFixture) -> None:
    """Test that @timed logs asynchronous execution time at DEBUG level."""
    caplog.set_level(logging.DEBUG)

    @timed
    async def slow_async(x: int) -> int:
        await asyncio.sleep(0.01)
        return x * 2

    res = asyncio.run(slow_async(5))
    assert res == 10
    # Filter to only get records from taskforge.decorators
    decorator_records = [r for r in caplog.records if r.name == "taskforge.decorators"]
    assert len(decorator_records) == 1
    assert decorator_records[0].levelno == logging.DEBUG
    assert "slow_async" in decorator_records[0].message
    assert "executed in" in decorator_records[0].message


# =====================================================================
# 2. Tests for @retry
# =====================================================================

def test_retry_sync_success_eventually() -> None:
    """Test sync @retry succeeds if within the attempts limit."""
    calls = 0

    @retry(attempts=3, exceptions=ValueError, backoff=0.001)
    def fail_twice(x: int) -> int:
        nonlocal calls
        calls += 1
        if calls < 3:
            raise ValueError("Failure")
        return x

    assert fail_twice(10) == 10
    assert calls == 3


def test_retry_sync_failure() -> None:
    """Test sync @retry raises the final exception if all attempts fail."""
    calls = 0

    @retry(attempts=3, exceptions=(ValueError, TypeError), backoff=0.001)
    def fail_always() -> None:
        nonlocal calls
        calls += 1
        raise ValueError(f"Fail {calls}")

    with pytest.raises(ValueError) as excinfo:
        fail_always()
    assert "Fail 3" in str(excinfo.value)
    assert calls == 3


def test_retry_async_success_eventually() -> None:
    """Test async @retry succeeds if within the attempts limit."""
    calls = 0

    @retry(attempts=3, exceptions=ValueError, backoff=0.001)
    async def fail_twice_async(x: int) -> int:
        nonlocal calls
        calls += 1
        if calls < 3:
            raise ValueError("Failure")
        return x

    assert asyncio.run(fail_twice_async(20)) == 20
    assert calls == 3


def test_retry_async_failure() -> None:
    """Test async @retry raises the final exception if all attempts fail."""
    calls = 0

    @retry(attempts=4, exceptions=ValueError, backoff=0.001)
    async def fail_always_async() -> None:
        nonlocal calls
        calls += 1
        raise ValueError(f"Fail {calls}")

    with pytest.raises(ValueError) as excinfo:
        asyncio.run(fail_always_async())
    assert "Fail 4" in str(excinfo.value)
    assert calls == 4


def test_retry_invalid_parameters() -> None:
    """Test validation of decorator parameters."""
    with pytest.raises(ValueError):
        retry(attempts=0, exceptions=ValueError, backoff=0.1)

    with pytest.raises(ValueError):
        retry(attempts=2, exceptions=ValueError, backoff=-0.5)


# =====================================================================
# 3. Tests for @memoize
# =====================================================================

def test_memoize_sync() -> None:
    """Test sync @memoize correctly caches calls and updates stats."""
    calls = 0

    @memoize
    def add(a: int, b: int) -> int:
        nonlocal calls
        calls += 1
        return a + b

    # First call: miss
    assert add(2, 3) == 5
    info = add.cache_info()  # type: ignore[attr-defined]
    assert info.hits == 0
    assert info.misses == 1
    assert info.currsize == 1
    assert calls == 1

    # Second call (same args): hit
    assert add(2, 3) == 5
    info = add.cache_info()  # type: ignore[attr-defined]
    assert info.hits == 1
    assert info.misses == 1
    assert info.currsize == 1
    assert calls == 1

    # Different kwargs: miss
    assert add(2, b=3) == 5
    info = add.cache_info()  # type: ignore[attr-defined]
    assert info.hits == 1
    assert info.misses == 2
    assert info.currsize == 2
    assert calls == 2

    # Clear cache
    add.cache_clear()  # type: ignore[attr-defined]
    info = add.cache_info()  # type: ignore[attr-defined]
    assert info.hits == 0
    assert info.misses == 0
    assert info.currsize == 0

    # Call again after clear: miss
    assert add(2, 3) == 5
    info = add.cache_info()  # type: ignore[attr-defined]
    assert info.hits == 0
    assert info.misses == 1
    assert info.currsize == 1


def test_memoize_async() -> None:
    """Test async @memoize correctly caches awaited results and updates stats."""
    calls = 0

    @memoize
    async def add_async(a: int, b: int) -> int:
        nonlocal calls
        calls += 1
        await asyncio.sleep(0.001)
        return a + b

    # First call: miss
    assert asyncio.run(add_async(4, 5)) == 9
    info = add_async.cache_info()  # type: ignore[attr-defined]
    assert info.hits == 0
    assert info.misses == 1
    assert info.currsize == 1
    assert calls == 1

    # Second call: hit
    assert asyncio.run(add_async(4, 5)) == 9
    info = add_async.cache_info()  # type: ignore[attr-defined]
    assert info.hits == 1
    assert info.misses == 1
    assert info.currsize == 1
    assert calls == 1


# =====================================================================
# 4. Tests for @validate_types
# =====================================================================

def test_validate_types_sync_basic() -> None:
    """Test type validation for simple sync functions."""

    @validate_types
    def greet(name: str, age: int, height: float | None = None) -> str:
        return f"{name}-{age}-{height}"

    # Valid calls
    assert greet("Alice", 30) == "Alice-30-None"
    assert greet("Bob", 25, 1.75) == "Bob-25-1.75"

    # Mismatched name (str expected, got int)
    with pytest.raises(TypeError) as excinfo:
        greet(123, 30)  # type: ignore[arg-type]
    assert "must be of type <class 'str'>" in str(excinfo.value)

    # Mismatched age (int expected, got str)
    with pytest.raises(TypeError) as excinfo:
        greet("Alice", "thirty")  # type: ignore[arg-type]
    assert "must be of type <class 'int'>" in str(excinfo.value)

    # Mismatched height (float | None expected, got str)
    with pytest.raises(TypeError):
        greet("Alice", 30, "tall")  # type: ignore[arg-type]


def test_validate_types_sync_complex() -> None:
    """Test type validation for complex subscripted generic types."""

    @validate_types
    def process_data(
        items: list[int],
        metadata: dict[str, float | None],
        tags: set[str] | None = None,
    ) -> None:
        pass

    # Valid
    process_data([1, 2, 3], {"x": 1.5, "y": None}, {"tag1"})

    # Invalid list item type
    with pytest.raises(TypeError):
        process_data([1, "two", 3], {"x": 1.5})  # type: ignore[list-item]

    # Invalid dict key type
    with pytest.raises(TypeError):
        process_data([1, 2], {123: 1.5})  # type: ignore[dict-item]

    # Invalid dict value type
    with pytest.raises(TypeError):
        process_data([1, 2], {"x": "one"})  # type: ignore[dict-item]

    # Invalid tags (set of int instead of set of str)
    with pytest.raises(TypeError):
        process_data([1, 2], {"x": 1.5}, {1, 2})  # type: ignore[arg-type]


def test_validate_types_async() -> None:
    """Test type validation for async functions."""

    @validate_types
    async def add_numbers(x: float, y: float) -> float:
        return x + y

    # Valid
    assert asyncio.run(add_numbers(1.5, 2.5)) == 4.0

    # Invalid
    with pytest.raises(TypeError):
        asyncio.run(add_numbers("1.5", 2.5))  # type: ignore[arg-type]


def test_validate_types_var_args() -> None:
    """Test type validation for *args and **kwargs."""

    @validate_types
    def sum_all(*numbers: int) -> int:
        return sum(numbers)

    # Valid
    assert sum_all(1, 2, 3, 4) == 10

    # Invalid
    with pytest.raises(TypeError) as excinfo:
        sum_all(1, "two", 3)  # type: ignore[arg-type]
    assert "must be of type <class 'int'>" in str(excinfo.value)
