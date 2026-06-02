from __future__ import annotations

import logging
import sqlite3
import time
from contextlib import contextmanager
from pathlib import Path
from types import TracebackType
from typing import Iterator

from taskforge.exceptions import SchedulerStateError

LOGGER = logging.getLogger(__name__)

class SchedulerSession:
    """Context manager for managing a sqlite scheduler session."""
    def __init__(self, db_path: str | Path):
        self.db_path = Path(db_path)
        self.connection: sqlite3.Connection | None = None
        self._activ = False

    def __enter__(self)-> sqlite3.Connection:
         if self._activ:
             raise SchedulerStateError("SchedulerSession is already active")
         self.connection = sqlite3.connect(self.db_path)
         self._activ = True
         return self.connection
    
    def __exit__(
            self,
            exc_type:type[BaseException] | None,
            exc_value: BaseException | None,
            traceback:TracebackType | None
            )-> None:
        if self.connection is None:
            return
        
        if exc_type is None:
            self.connection.commit()
        else:
            self.connection.rollback()
        
        self.connection.close()
        self.connection = None
        self._activ = False

@contextmanager
def timed_block(label: str)-> Iterator(None):
        """Measure and log elapsed time for a code block."""
        start_time = time.perf_counter()

        try:
             yield
        finally:
             elapsed = time.perf_counter() - start_time
             LOGGER.info("%s took %.4f seconds", label, elapsed)

        