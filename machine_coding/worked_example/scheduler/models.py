"""Written at minute 12. Four minutes. The highest-leverage file.

Naming the domain (Task, TaskStatus, Priority) is what makes the rest of the
design fall out. Dataclasses and enums only -- no logic, no locks.
"""

import time
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Callable, Optional


class Priority(int, Enum):
    """int-Enum so it sorts naturally inside a PriorityQueue (lowest first)."""
    HIGH = 0
    MEDIUM = 1
    LOW = 2


class TaskStatus(str, Enum):
    """str-Enum so it prints readably in the demo."""
    PENDING = "PENDING"        # accepted, waiting for its scheduled time
    QUEUED = "QUEUED"          # in the ready queue, waiting for a worker
    RUNNING = "RUNNING"
    SUCCEEDED = "SUCCEEDED"
    FAILED = "FAILED"          # exhausted all retries
    CANCELLED = "CANCELLED"

    @property
    def is_terminal(self) -> bool:
        return self in (TaskStatus.SUCCEEDED, TaskStatus.FAILED,
                        TaskStatus.CANCELLED)


@dataclass
class Task:
    id: str
    name: str
    fn: Callable[..., Any]
    args: tuple = ()
    kwargs: dict = field(default_factory=dict)   # NOT `= {}` -- shared mutable default
    priority: Priority = Priority.MEDIUM

    status: TaskStatus = TaskStatus.PENDING
    attempts: int = 0
    result: Any = None
    error: Optional[str] = None

    run_at: float = field(default_factory=time.monotonic)
    created_at: float = field(default_factory=time.time)
    started_at: Optional[float] = None
    finished_at: Optional[float] = None

    @property
    def duration_ms(self) -> Optional[float]:
        if self.started_at is None or self.finished_at is None:
            return None
        return (self.finished_at - self.started_at) * 1000

    def snapshot(self) -> "TaskView":
        """Hand callers an immutable copy, never the live object.

        If we returned `self`, a caller could mutate task state outside our
        lock -- the critical section would escape our control.
        """
        return TaskView(
            id=self.id, name=self.name, status=self.status,
            priority=self.priority, attempts=self.attempts,
            result=self.result, error=self.error,
            duration_ms=self.duration_ms,
        )


@dataclass(frozen=True)
class TaskView:
    """Immutable view handed out by the public API. Trivially thread-safe."""
    id: str
    name: str
    status: TaskStatus
    priority: Priority
    attempts: int
    result: Any = None
    error: Optional[str] = None
    duration_ms: Optional[float] = None
