"""File 3 of 6. THE HIGHEST-LEVERAGE FILE. Four minutes.

Dataclasses and enums only -- no logic, no locks, no I/O.

Writing this first forces you to name your domain, and once the nouns are
named the rest of the design mostly writes itself. Enums instead of magic
strings is free credit and takes ten seconds.
"""

import time
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Optional


class Status(str, Enum):
    """str-Enum so it prints readably in the demo and compares to strings."""
    PENDING = "PENDING"
    ACTIVE = "ACTIVE"
    COMPLETED = "COMPLETED"
    FAILED = "FAILED"
    CANCELLED = "CANCELLED"


class Priority(int, Enum):
    """int-Enum so it sorts naturally in a PriorityQueue."""
    HIGH = 1
    MEDIUM = 2
    LOW = 3


@dataclass
class Entity:
    id: str
    name: str
    status: Status = Status.PENDING
    priority: Priority = Priority.MEDIUM
    created_at: float = field(default_factory=time.time)
    metadata: dict[str, Any] = field(default_factory=dict)
    # ^ default_factory, NOT `metadata: dict = {}`. A mutable default is
    #   shared across every instance -- a classic bug an interviewer will spot.

    def is_terminal(self) -> bool:
        """Small, pure helpers on the model are fine. Business rules are not."""
        return self.status in (Status.COMPLETED, Status.FAILED, Status.CANCELLED)


@dataclass(frozen=True)
class Result:
    """frozen=True for value objects you pass around after the fact --
    immutable objects are trivially thread-safe."""
    entity_id: str
    success: bool
    value: Optional[Any] = None
    error: Optional[str] = None
    duration_ms: float = 0.0
