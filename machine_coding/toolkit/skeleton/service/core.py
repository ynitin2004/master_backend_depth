"""File 5 of 6. Three minutes -- SIGNATURES ONLY at first.

The orchestration layer: the public API the demo and tests call. It holds no
state of its own; it delegates to the store.

At minute 20 every method here is a stub. Fill them in during 0:20-0:55.
"""

import itertools
import threading
from typing import Callable, Optional

from .exceptions import InvalidStateError
from .models import Entity, Priority, Status


class Service:
    def __init__(self, store=None, max_entities: int = 1000):
        # Dependency injection, not `self._store = EntityStore()` hardcoded.
        # Lets you say "and I'd swap in a persistent store here" for free.
        from .store import EntityStore
        self._store = store or EntityStore()
        self._max_entities = max_entities
        self._ids = itertools.count(1)
        self._id_lock = threading.Lock()

    # ------------------------------------------------------------- commands
    def create(self, name: str, priority: Priority = Priority.MEDIUM) -> Entity:
        if not name:
            raise ValueError("name must not be empty")
        entity = Entity(id=self._next_id(), name=name, priority=priority)
        self._store.add(entity)
        return entity

    def activate(self, entity_id: str) -> Entity:
        entity = self._store.get(entity_id)
        # A state-machine guard. Interviewers love seeing illegal transitions
        # rejected rather than silently allowed.
        if entity.status is not Status.PENDING:
            raise InvalidStateError(
                f"cannot activate {entity_id}: status is {entity.status}")
        return self._store.update_status(entity_id, Status.ACTIVE)

    def complete(self, entity_id: str) -> Entity:
        return self._store.update_status(entity_id, Status.COMPLETED)

    def cancel(self, entity_id: str) -> Entity:
        entity = self._store.get(entity_id)
        if entity.is_terminal():
            raise InvalidStateError(f"{entity_id} is already {entity.status}")
        return self._store.update_status(entity_id, Status.CANCELLED)

    # -------------------------------------------------------------- queries
    def get(self, entity_id: str) -> Entity:
        return self._store.get(entity_id)

    def list(self, status: Optional[Status] = None) -> list[Entity]:
        if status is None:
            return self._store.list_all()
        return self._store.list_all(lambda e: e.status is status)

    def stats(self) -> dict[str, int]:
        counts = {s.value: 0 for s in Status}
        for entity in self._store.list_all():
            counts[entity.status.value] += 1
        counts["total"] = self._store.count()
        return counts

    # -------------------------------------------------------------- helpers
    def _next_id(self) -> str:
        with self._id_lock:
            return f"ent-{next(self._ids)}"

    # ------------------------------------------------------------- lifecycle
    def shutdown(self, wait: bool = True, timeout: float = 5.0) -> None:
        """No background threads in the skeleton, but ALWAYS expose this.

        "How do you shut it down?" is the most common follow-up question in
        the whole round. Having an answer already written is free points.
        """
        return None
