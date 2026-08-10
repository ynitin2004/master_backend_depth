"""The five tests. Write these at 0:55-1:10, in this order.

Run:  python -m unittest test_service.py -v

Plain unittest. No pytest, no fixtures, no mocks -- you don't have time and
they don't earn anything.
"""

import threading
import unittest

from service import Priority, Service, Status
from service.exceptions import (
    DuplicateEntityError,
    EntityNotFoundError,
    InvalidStateError,
)
from service.models import Entity
from service.store import EntityStore


class TestService(unittest.TestCase):

    def setUp(self):
        self.service = Service()

    # ------------------------------------------------------------- 1. happy
    def test_create_and_lifecycle(self):
        entity = self.service.create("deploy", Priority.HIGH)

        self.assertEqual(entity.status, Status.PENDING)
        self.assertEqual(entity.priority, Priority.HIGH)

        self.service.activate(entity.id)
        self.assertEqual(self.service.get(entity.id).status, Status.ACTIVE)

        self.service.complete(entity.id)
        self.assertEqual(self.service.get(entity.id).status, Status.COMPLETED)
        self.assertTrue(self.service.get(entity.id).is_terminal())

    # --------------------------------------------------------------- 2. edge
    def test_empty_and_filtering(self):
        self.assertEqual(self.service.list(), [])
        self.assertEqual(self.service.stats()["total"], 0)

        a = self.service.create("a")
        self.service.create("b")
        self.service.cancel(a.id)

        self.assertEqual(len(self.service.list()), 2)
        self.assertEqual([e.id for e in self.service.list(Status.CANCELLED)], [a.id])
        self.assertEqual(self.service.stats()["PENDING"], 1)

    # -------------------------------------------------------------- 3. error
    def test_error_paths(self):
        with self.assertRaises(EntityNotFoundError):
            self.service.get("does-not-exist")

        with self.assertRaises(ValueError):
            self.service.create("")

        entity = self.service.create("x")
        self.service.cancel(entity.id)
        with self.assertRaises(InvalidStateError):
            self.service.activate(entity.id)     # terminal -> can't activate
        with self.assertRaises(InvalidStateError):
            self.service.cancel(entity.id)       # already cancelled

        store = EntityStore()
        store.add(Entity(id="dup", name="x"))
        with self.assertRaises(DuplicateEntityError):
            store.add(Entity(id="dup", name="y"))

    # -------------------------------------------------- 4. THE CONCURRENCY ONE
    def test_concurrent_creates(self):
        """Memorise this shape. It is the same in every machine coding round."""
        errors = []
        n_threads, per_thread = 10, 100

        def worker(worker_id):
            try:
                for i in range(per_thread):
                    self.service.create(f"w{worker_id}-{i}")
            except Exception as exc:             # noqa: BLE001
                errors.append(exc)

        threads = [threading.Thread(target=worker, args=(i,))
                   for i in range(n_threads)]
        for t in threads: t.start()
        for t in threads: t.join(timeout=15)

        self.assertFalse(any(t.is_alive() for t in threads), "threads hung")
        self.assertFalse(errors, f"errors under concurrency: {errors[:3]}")

        # Assert INVARIANTS, never ordering.
        entities = self.service.list()
        self.assertEqual(len(entities), n_threads * per_thread)
        self.assertEqual(len({e.id for e in entities}), n_threads * per_thread,
                         "duplicate ids -> the id generator raced")

    def test_concurrent_state_transitions(self):
        """Only ONE thread may win a state transition -- check-then-act."""
        entity = self.service.create("contested")
        winners = []
        lock = threading.Lock()

        def try_activate():
            try:
                self.service.activate(entity.id)
                with lock:
                    winners.append(threading.current_thread().name)
            except InvalidStateError:
                pass

        threads = [threading.Thread(target=try_activate) for _ in range(20)]
        for t in threads: t.start()
        for t in threads: t.join(timeout=10)

        self.assertEqual(len(winners), 1,
                         f"{len(winners)} threads activated the same entity")

    # ----------------------------------------------------------- 5. shutdown
    def test_shutdown_is_clean(self):
        self.service.create("x")
        self.service.shutdown(wait=True, timeout=2.0)
        # Idempotent: calling it twice must not blow up.
        self.service.shutdown()


if __name__ == "__main__":
    unittest.main(verbosity=2)
