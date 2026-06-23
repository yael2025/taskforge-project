# TaskForge

TaskForge is a Python library for task scheduling and execution with support for synchronous and asynchronous workflows, dependency management, decorators, descriptors, streams, and execution backends.

## Features

* Immutable `Task` objects
* Task dependency management
* Synchronous scheduler
* Asynchronous scheduler with concurrency limits
* Task cancellation and timeout support
* Execution backends
* Decorators for retry, timing, memoization, and validation
* Descriptors for runtime validation
* Streams and event routing utilities
* Registry and configuration support
* Session management with SQLite
* Logging configuration
* Comprehensive test suite

## Project Structure

```
taskforge-project
│
├── taskforge
│   ├── async_scheduler.py
│   ├── decorators.py
│   ├── descriptors.py
│   ├── executors.py
│   ├── exceptions.py
│   ├── logging_config.py
│   ├── registry.py
│   ├── scheduler.py
│   ├── session.py
│   ├── streams.py
│   ├── task.py
│   └── utils.py
│
├── tests
├── README.md
├── DESIGN.md
├── pyproject.toml
└── requirements.txt
```

## Installation

Clone the repository:

```bash
git clone https://github.com/yael2025/taskforge-project.git
cd taskforge-project
```

Install dependencies:

```bash
pip install -r requirements.txt
```

## Example

```python
from taskforge import Task

def hello():
    return "hello world"

task = Task(
    task_id="1",
    name="example",
    payload=hello,
)

print(task.payload())
```

## Testing

Run all tests:

```bash
python -m pytest
```

Run tests with coverage:

```bash
python -m pytest --cov=taskforge
```

## Quality Checks

Run Ruff:

```bash
ruff check .
ruff format .
```

## Test Results

* 69 tests passed
* 90% code coverage

## Technologies

* Python 3.13
* pytest
* pytest-cov
* asyncio
* sqlite3
* logging
* ThreadPoolExecutor
* Ruff

## Author

Yael Pinhas
