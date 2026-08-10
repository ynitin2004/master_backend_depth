"""File 4 of 6. Three minutes.

Owns the shared state AND the lock. Nothing else in the codebase locks.

"One owner per piece of state" is the rule that keeps concurrency tractable
when you're under time pressure. If two classes both lock, you have to reason
about lock ordering; if only one does, you never do.
"""

import threading
from typing import Callable, Optional

from .exceptions import DuplicateEntityError, EntityNotFoundError
from .models import Entity, Status


class EntityStore:
    def __init__(self):
        self._entities: dict[str, Entity] = {}
        # RLock, not Lock: these methods call each other (update -> get).
        # A plain Lock would deadlock against itself.
        self._lock = threading.RLock()

    def add(self, entity: Entity) -> None:
        with self._lock:
            # Check-then-act, inside ONE lock acquisition. Say this out loud:
            # "the existence check and the insert have to be atomic together,
            #  otherwise two threads both see 'absent' and both insert."
            if entity.id in self._entities:
                raise DuplicateEntityError(entity.id)
            self._entities[entity.id] = entity

    def get(self, entity_id: str) -> Entity:
        with self._lock:
            entity = self._entities.get(entity_id)
            if entity is None:
                raise EntityNotFoundError(entity_id)
            return entity

    def update_status(self, entity_id: str, new_status: Status) -> Entity:
        """Read-modify-write under the lock.

        Never hand the caller a live object and let them mutate it outside --
        that moves the critical section outside your control.
        """
        with self._lock:
            entity = self.get(entity_id)          # re-entrant: needs RLock
            entity.status = new_status
            return entity

    def remove(self, entity_id: str) -> Entity:
        with self._lock:
            entity = self._entities.pop(entity_id, None)
            if entity is None:
                raise EntityNotFoundError(entity_id)
            return entity

    def list_all(self, predicate: Optional[Callable[[Entity], bool]] = None) -> list[Entity]:
        with self._lock:
            items = list(self._entities.values())   # a COPY, not the live view
        # Filter OUTSIDE the lock: the predicate is caller-supplied code and
        # you never run unknown code while holding a lock.
        return [e for e in items if predicate is None or predicate(e)]

    def count(self) -> int:
        with self._lock:
            return len(self._entities)

    def __contains__(self, entity_id: str) -> bool:
        with self._lock:
            return entity_id in self._entities
