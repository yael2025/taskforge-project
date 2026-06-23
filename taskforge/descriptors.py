from __future__ import annotations

from typing import Any


class Typed:
    """Descriptor that validates a value type."""

    def __init__(self, expected_type: type[Any]) -> None:
        self.expected_type = expected_type
        self.private_name = ""

    def __set_name__(self, owner: type[Any], name: str) -> None:
        self.private_name = f"_{name}"

    def __get__(self, instance: Any, owner: type[Any]) -> Any:
        if instance is None:
            return self

        return getattr(instance, self.private_name)

    def __set__(self, instance: Any, value: Any) -> None:
        if not isinstance(value, self.expected_type):
            raise TypeError(
                f"Expected {self.expected_type.__name__}, "
                f"got {type(value).__name__}"
            )

        setattr(instance, self.private_name, value)


class Positive:
    """Descriptor that validates a positive value."""

    def __init__(self) -> None:
        self.private_name = ""

    def __set_name__(self, owner: type[Any], name: str) -> None:
        self.private_name = f"_{name}"

    def __get__(self, instance: Any, owner: type[Any]) -> Any:
        if instance is None:
            return self

        return getattr(instance, self.private_name)

    def __set__(self, instance: Any, value: Any) -> None:
        if value <= 0:
            raise ValueError("Value must be positive")

        setattr(instance, self.private_name, value)


class Range:
    """Descriptor that validates a value is inside a range."""

    def __init__(self, low: int, high: int) -> None:
        self.low = low
        self.high = high
        self.private_name = ""

    def __set_name__(self, owner: type[Any], name: str) -> None:
        self.private_name = f"_{name}"

    def __get__(self, instance: Any, owner: type[Any]) -> Any:
        if instance is None:
            return self

        return getattr(instance, self.private_name)

    def __set__(self, instance: Any, value: Any) -> None:
        if not self.low <= value <= self.high:
            raise ValueError(
                f"Value must be between {self.low} and {self.high}"
            )

        setattr(instance, self.private_name, value)


class NonEmptyString:
    """Descriptor that validates a non-empty string."""

    def __init__(self) -> None:
        self.private_name = ""

    def __set_name__(self, owner: type[Any], name: str) -> None:
        self.private_name = f"_{name}"

    def __get__(self, instance: Any, owner: type[Any]) -> Any:
        if instance is None:
            return self

        return getattr(instance, self.private_name)

    def __set__(self, instance: Any, value: Any) -> None:
        if not isinstance(value, str):
            raise TypeError("Value must be a string")

        if not value.strip():
            raise ValueError("Value cannot be empty")

        setattr(instance, self.private_name, value)


class Composed:
    """Descriptor that combines multiple validation descriptors."""

    def __init__(self, *descriptors: Any) -> None:
        self.descriptors = descriptors
        self.private_name = ""

    def __set_name__(self, owner: type[Any], name: str) -> None:
        self.private_name = f"_{name}"

        for descriptor in self.descriptors:
            descriptor.__set_name__(owner, name)

    def __get__(self, instance: Any, owner: type[Any]) -> Any:
        if instance is None:
            return self

        return getattr(instance, self.private_name)

    def __set__(self, instance: Any, value: Any) -> None:
        for descriptor in self.descriptors:
            descriptor.__set__(instance, value)

        setattr(instance, self.private_name, value)