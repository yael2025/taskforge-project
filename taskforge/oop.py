from __future__ import annotations
import logging
from typing import Any

class LoggingMixin:
    """Add a class-based logger property."""

    @property
    def log(self) -> logging.Logger:
        """Return a logger named after the class."""
        return logging.getLogger(self.__class__.__name__)
    
class SerializableMixin:
    """Add dictionary serialization support."""

    __serializable_fields__: tuple[str, ...]

    def __init_subclass__(cls) -> None:
        """Require subclasses to define serializable fields."""
        super().__init_subclass__()

        if not hasattr(cls, "__serializable_fields__"):
            raise TypeError(
                "SerializableMixin subclasses must define "
                "__serializable_fields__"
            )
    def to_dict(self) -> dict[str, Any]:
        """Convert selected fields into a dictionary."""
        return {
            field: getattr(self, field)
            for field in self.__serializable_fields__
        }
    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> Any:
        """Create an instance from a dictionary."""
        return cls(**data)

class SlottedConfig(LoggingMixin, SerializableMixin):
    """Small configuration object that uses slots."""

    __slots__ = ("name", "value")
    __serializable_fields__ = ("name", "value")

    def __init__(self, name: str, value: int) -> None:
        self.name = name
        self.value = value