from __future__ import annotations

import pytest

from taskforge.descriptors import Composed, NonEmptyString, Positive, Range, Typed


class DummyClass:
    """A dummy class for testing individual descriptors."""

    typed_int = Typed(int)
    typed_str_list = Typed((str, list))
    positive_num = Positive()
    range_val = Range(10, 20)
    non_empty = NonEmptyString()

    priority = Composed(Typed(int), Positive(), Range(1, 10))


def test_typed_descriptor() -> None:
    """Test that the Typed descriptor enforces correct types."""
    obj = DummyClass()

    # Valid sets
    obj.typed_int = 42
    assert obj.typed_int == 42

    obj.typed_str_list = "hello"
    assert obj.typed_str_list == "hello"
    obj.typed_str_list = ["a", "b"]
    assert obj.typed_str_list == ["a", "b"]

    # Invalid sets
    with pytest.raises(TypeError):
        obj.typed_int = "not an int"  # type: ignore[assignment]

    with pytest.raises(TypeError):
        obj.typed_str_list = 123  # type: ignore[assignment]


def test_positive_descriptor() -> None:
    """Test that the Positive descriptor enforces positive numbers."""
    obj = DummyClass()

    # Valid sets
    obj.positive_num = 1
    assert obj.positive_num == 1
    obj.positive_num = 0.5
    assert obj.positive_num == 0.5

    # Invalid sets
    with pytest.raises(ValueError):
        obj.positive_num = 0

    with pytest.raises(ValueError):
        obj.positive_num = -5

    with pytest.raises(TypeError):
        obj.positive_num = "not a number"  # type: ignore[assignment]


def test_range_descriptor() -> None:
    """Test that the Range descriptor enforces inclusive boundaries."""
    obj = DummyClass()

    # Valid sets
    obj.range_val = 10
    assert obj.range_val == 10
    obj.range_val = 15
    assert obj.range_val == 15
    obj.range_val = 20
    assert obj.range_val == 20

    # Invalid sets
    with pytest.raises(ValueError):
        obj.range_val = 9

    with pytest.raises(ValueError):
        obj.range_val = 21

    with pytest.raises(TypeError):
        obj.range_val = "not a number"  # type: ignore[assignment]


def test_non_empty_string_descriptor() -> None:
    """Test that the NonEmptyString descriptor enforces string constraints."""
    obj = DummyClass()

    # Valid sets
    obj.non_empty = "valid"
    assert obj.non_empty == "valid"
    obj.non_empty = "  valid with spaces  "
    assert obj.non_empty == "  valid with spaces  "

    # Invalid sets
    with pytest.raises(ValueError):
        obj.non_empty = ""

    with pytest.raises(ValueError):
        obj.non_empty = "   "

    with pytest.raises(TypeError):
        obj.non_empty = 123  # type: ignore[assignment]


def test_composed_descriptor() -> None:
    """Test composing multiple descriptors inside the Composed wrapper."""
    obj = DummyClass()

    # Valid sets (int, positive, range 1 to 10)
    obj.priority = 5
    assert obj.priority == 5

    obj.priority = 10
    assert obj.priority == 10

    # Mismatched type (fails Typed(int))
    with pytest.raises(TypeError):
        obj.priority = 5.5  # type: ignore[assignment]

    # Mismatched sign (fails Positive())
    with pytest.raises(ValueError):
        obj.priority = 0

    # Mismatched boundaries (fails Range(1, 10))
    with pytest.raises(ValueError):
        obj.priority = 11
