"""Written at minute 16. Three minutes.

Owns ALL task state and the only lock over it. Nothing else in the package
touches self._tasks.
"""

import threading
from typing import Callable, Optional

from .exceptions import TaskNotFoundError
from .models import Task, TaskStatus, TaskView


class TaskStore:
    def __init__(self):
        self._tasks: dict[str, Task] = {}
        # RLock: these methods call each other (transition -> _get_locked).
        self._lock = threading.RLock()

    def add(self, task: Task) -> None:
        with self._lock:
            self._tasks[task.id] = task

    def get(self, task_id: str) -> TaskView:
        """Public read -> returns an immutable snapshot, never the live Task."""
        with self._lock:
            return self._require(task_id).snapshot()

    def transition(self, task_id: str, new_status: TaskStatus,
                   guard: Optional[Callable[[Task], bool]] = None,
                   mutate: Optional[Callable[[Task], None]] = None) -> bool:
        """Guarded state transition. Returns True if it happened.

        THE most important method in the file. The guard check and the status
        write happen inside ONE lock acquisition -- this is a check-then-act,
        and splitting it is how you get two workers running the same task.
        """
        with self._lock:
            task = self._require(task_id)
            if guard is not None and not guard(task):
                return False
            task.status = new_status
            if mutate is not None:
                mutate(task)
            return True

    def update(self, task_id: str, mutate: Callable[[Task], None]) -> None:
        with self._lock:
            mutate(self._require(task_id))

    def all(self) -> list[TaskView]:
        with self._lock:
            return [t.snapshot() for t in self._tasks.values()]

    def count_by_status(self) -> dict[str, int]:
        counts = {s.value: 0 for s in TaskStatus}
        with self._lock:
            for task in self._tasks.values():
                counts[task.status.value] += 1
        return counts

    def __len__(self) -> int:
        with self._lock:
            return len(self._tasks)

    def __contains__(self, task_id: str) -> bool:
        with self._lock:
            return task_id in self._tasks

    # ------------------------------------------------------------- internal
    def _require(self, task_id: str) -> Task:
        """Caller must hold the lock."""
        task = self._tasks.get(task_id)
        if task is None:
            raise TaskNotFoundError(task_id)
        return task
