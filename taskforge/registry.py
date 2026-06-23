from __future__ import annotations

from abc import ABCMeta
from typing import Any

from taskforge.descriptors import Typed
from taskforge.exceptions import TaskForgeError


class ExecutorMeta(ABCMeta):
    """Metaclass that registers concrete executor classes."""

    _registry: dict[str, type[Any]] = {}

    def __new__(
        mcls,
        name: str,
        bases: tuple[type[Any], ...],
        namespace: dict[str, Any],
    ) -> ExecutorMeta:
        cls = super().__new__(mcls, name, bases, namespace)

        executor_name = namespace.get("executor_name")
        is_abstract = bool(getattr(cls, "__abstractmethods__", False))

        if executor_name and not is_abstract:
            if executor_name in mcls._registry:
                raise TaskForgeError(
                    f"Executor name already registered: {executor_name}"
                )

            mcls._registry[executor_name] = cls

        return cls

    @classmethod
    def get(mcls, name: str) -> type[Any]:
        """Return a registered executor class by name."""
        try:
            return mcls._registry[name]
        except KeyError as error:
            raise TaskForgeError(f"Unknown executor: {name}") from error


class ConfigMeta(type):
    """Metaclass that installs descriptors from __config_schema__."""

    def __new__(
        mcls,
        name: str,
        bases: tuple[type[Any], ...],
        namespace: dict[str, Any],
    ) -> ConfigMeta:
        schema = namespace.get("__config_schema__")

        if schema is None:
            raise TaskForgeError(
                f"{name} must define __config_schema__"
            )

        for field_name, field_type in schema.items():
            namespace[field_name] = Typed(field_type)

        return super().__new__(mcls, name, bases, namespace)