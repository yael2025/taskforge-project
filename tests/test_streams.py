from __future__ import annotations

import pytest

from taskforge.streams import event_router
from taskforge.streams import merge_sorted_streams
from taskforge.streams import paginate
from taskforge.streams import task_batches


def test_task_batches() -> None:
    """Test batching tasks into fixed-size groups."""
    result = list(task_batches([1, 2, 3, 4, 5], 2))

    assert result == [[1, 2], [3, 4], [5]]


def test_merge_sorted_streams() -> None:
    """Test lazy merging of sorted streams."""
    result = list(
        merge_sorted_streams(
            [1, 3, 5],
            [2, 4, 6],
        )
    )

    assert result == [1, 2, 3, 4, 5, 6]


def test_merge_sorted_streams_with_key() -> None:
    """Test merging sorted streams using a key function."""
    result = list(
        merge_sorted_streams(
            [{"value": 1}, {"value": 4}],
            [{"value": 2}, {"value": 3}],
            key=lambda item: item["value"],
        )
    )

    assert [item["value"] for item in result] == [1, 2, 3, 4]


def test_paginate() -> None:
    """Test pagination generator."""

    data = [1, 2, 3, 4, 5]

    def query(offset: int, limit: int) -> list[int]:
        return data[offset:offset + limit]

    result = list(paginate(query, 2))

    assert result == [1, 2, 3, 4, 5]


def test_paginate_invalid_page_size() -> None:
    """Test invalid page size."""
    with pytest.raises(ValueError):
        list(paginate(lambda offset, limit: [], 0))


def test_event_router_dispatches_registered_handler() -> None:
    """Test event router dispatches events to registered handlers."""
    received: list[str] = []

    def handler(event: dict[str, object]) -> None:
        received.append(str(event["message"]))

    router = event_router()
    next(router)

    router.send(
        {
            "type": "register",
            "name": "hello",
            "handler": handler,
        }
    )

    router.send(
        {
            "type": "hello",
            "message": "world",
        }
    )

    router.close()

    assert received == ["world"]


def test_event_router_ignores_none_and_unknown_events() -> None:
    """Test event router ignores None and unknown event types."""
    received: list[str] = []

    def handler(event: dict[str, object]) -> None:
        received.append(str(event["message"]))

    router = event_router()
    next(router)

    router.send(None)

    router.send(
        {
            "type": "unknown",
            "message": "ignored",
        }
    )

    router.close()

    assert received == []