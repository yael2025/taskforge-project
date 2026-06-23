from __future__ import annotations

import abc
import pytest

from taskforge.exceptions import TaskForgeError
from taskforge.registry import ConfigMeta, ExecutorMeta


# =====================================================================
# 1. Tests for ExecutorMeta
# =====================================================================

def test_executor_meta_registration() -> None:
    """Test concrete subclasses auto-registration and duplicate protection."""

    # Define a custom base using ExecutorMeta (mimicking BaseExecutor)
    class MockBaseExecutor(metaclass=ExecutorMeta):
        @abc.abstractmethod
        def run(self) -> None:
            pass

    # Abstract classes are NOT registered
    class AbstractSubclass(MockBaseExecutor):
        @abc.abstractmethod
        def another_abstract(self) -> None:
            pass

    # Verify AbstractSubclass is not in the registry
    with pytest.raises(TaskForgeError):
        ExecutorMeta.get("abstract_executor")

    # Concrete class with name - must auto-register
    class ValidExecutor(MockBaseExecutor):
        executor_name = "valid_exec"

        def run(self) -> None:
            pass

    # Should fetch successfully
    fetched = ExecutorMeta.get("valid_exec")
    assert fetched is ValidExecutor

    # Attempting duplicate name registration raises TaskForgeError
    with pytest.raises(TaskForgeError) as excinfo:

        class AnotherValidExecutor(MockBaseExecutor):
            executor_name = "valid_exec"

            def run(self) -> None:
                pass

    assert "already registered" in str(excinfo.value)


# =====================================================================
# 2. Tests for ConfigMeta
# =====================================================================

def test_config_meta_valid() -> None:
    """Test dynamic descriptor installation from a config schema."""

    class DbConfig(metaclass=ConfigMeta):
        __config_schema__ = {
            "host": str,
            "port": int,
            "timeout": float,
        }

    config = DbConfig()

    # Valid sets
    config.host = "localhost"
    config.port = 5432
    config.timeout = 5.0

    assert config.host == "localhost"
    assert config.port == 5432
    assert config.timeout == 5.0

    # Invalid sets raise TypeError from installed Typed descriptors
    with pytest.raises(TypeError):
        config.host = 123  # type: ignore[assignment]

    with pytest.raises(TypeError):
        config.port = "not an int"  # type: ignore[assignment]


def test_config_meta_missing_schema() -> None:
    """Test that missing or invalid schema raises TaskForgeError at definition."""

    # Missing schema raises TaskForgeError
    with pytest.raises(TaskForgeError) as excinfo:

        class InvalidConfig(metaclass=ConfigMeta):
            pass

    assert "must define the '__config_schema__' attribute" in str(excinfo.value)

    # Non-dictionary schema raises TaskForgeError
    with pytest.raises(TaskForgeError) as excinfo:

        class BadConfig(metaclass=ConfigMeta):
            __config_schema__ = ["host", "port"]  # type: ignore[assignment]

    assert "must be a dictionary" in str(excinfo.value)
