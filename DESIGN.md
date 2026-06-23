# TaskForge Design

## Overview

TaskForge is built as a modular Python package. Each module is responsible for one clear part of the system: task modeling, scheduling, execution, validation, persistence utilities, decorators, streams, and asynchronous execution.

The design goal was to keep the public API simple while using advanced Python features where they add real value.

## Task Model

The `Task` class is implemented as a frozen dataclass. This makes task objects immutable after creation, which helps prevent accidental changes while tasks are already scheduled.

Tasks are ordered by priority, creation time, and task id. Higher-priority tasks are sorted first, while older tasks run before newer tasks when priorities are equal.

## Scheduler

The synchronous `Scheduler` stores pending tasks in a dictionary by `task_id`. It supports Pythonic behavior:

- `len(scheduler)`
- `"task_id" in scheduler`
- `scheduler += task`
- iteration over tasks

Task ordering is delegated to `topological_sort`, which respects dependencies and priority.

## AsyncScheduler

`AsyncScheduler` supports asynchronous task execution with dependency handling, cancellation, timeout support, and concurrency limiting.

It uses:

- `asyncio.Queue` to hold ready tasks
- `asyncio.Lock` to protect shared state
- `asyncio.Event` to mark shutdown
- `asyncio.create_task` to run tasks concurrently

The scheduler tracks task status using internal dictionaries for results, errors, and status values.

## Decorators

The decorators module provides:

- `timed`
- `retry`
- `memoize`
- `validate_types`

Each decorator uses `functools.wraps` to preserve metadata. Decorators that wrap asynchronous functions detect coroutine functions and use `await` when needed.

`memoize` uses a closure-held dictionary instead of `functools.lru_cache`, as required by the assignment.

## Descriptors

The descriptor module includes validation descriptors:

- `Typed`
- `Positive`
- `Range`
- `NonEmptyString`
- `Composed`

Descriptors centralize validation logic and keep classes cleaner. The `Composed` descriptor allows several validation rules to be applied to one attribute.

## Metaclasses

`ExecutorMeta` registers concrete executor classes automatically by `executor_name`. This makes executor lookup extensible without hardcoding class names.

`ConfigMeta` validates configuration classes by requiring a `__config_schema__` dictionary and installing descriptors dynamically.

## Executors

The executor hierarchy separates execution strategies:

- `SyncExecutor`
- `ThreadPoolExecutorBackend`
- `AsyncExecutor`

This allows the scheduler system to support different execution styles without changing task definitions.

## Mixins and Slots

`LoggingMixin` provides a logger property named after the class.

`SerializableMixin` provides `to_dict` and `from_dict`, and uses `__init_subclass__` to enforce that subclasses define `__serializable_fields__`.

`SlottedConfig` uses `__slots__` to prevent unexpected attributes and reduce instance memory overhead.

## Session Management

`SchedulerSession` is a class-based context manager around SQLite. It commits on success, rolls back on exceptions, and always closes the connection.

`timed_block` is implemented with `contextlib.contextmanager` and logs elapsed execution time.

## Streams

The streams module provides lazy generator-based utilities:

- batching
- merging sorted streams
- pagination
- event routing with `send`

These functions avoid unnecessary list accumulation and support streaming-style processing.

## Testing

The project includes a pytest suite covering core behavior, edge cases, descriptors, decorators, schedulers, registry behavior, sessions, streams, executors, and async execution.

Current result:

- 69 tests passing
- 90% code coverage

## Trade-offs

The implementation favors readability and explicit behavior over maximum performance. Some internal scheduler state is exposed only for testing purposes. In a production library, those details would likely be wrapped with public query methods.