from __future__ import annotations

from dataclasses import dataclass
from dataclasses import field
from datetime import datetime
from typing import Any
from typing import Callable
from typing import Coroutine

from taskforge.exceptions import TaskValidationError

@dataclass(order=True, frozen=True)
class Task:
     """
    Represents a scheduled task.
    """
     
     sort_index: tuple[int, datetime] = field(
          init=False,
          repr=False
     )

     task_id: str
     name: str
    
     priority: int = 5

     dependencies: frozenset[str] = field(
          default_factory=frozenset
     )

     payload: Callable[..., Any] | Coroutine[Any, Any, Any] = field(
          default=None
     )
     created_at: datetime = field(
          default_factory=datetime.now
     )

     def __post_init__(self)-> None:
          
          if not self.task_id.strip():
               raise TaskValidationError(
                    "task_id cannot be empty"
               )
          if not self.name.strip():
               raise TaskValidationError(
                    "name cannot be empty"
               )
          if not 1<= self.priority<=10:
               raise TaskValidationError(
                "priority must be between 1 and 10"
            )
          if self.payload is None:
               raise TaskValidationError(
                    "payload is required"
               )
          
          object.__setattr__(
               self,
               "sort_ index",
               (-self.priority, self.created_at)
          )



