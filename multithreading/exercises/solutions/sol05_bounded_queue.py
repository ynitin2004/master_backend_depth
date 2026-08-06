"""Solution 5 - Bounded blocking queue from scratch.

The classic "implement a concurrency primitive" interview answer.
"""

import collections
import threading
import time


class BoundedQueue:
    def __init__(self, maxsize):
        if maxsize <= 0:
            raise ValueError("maxsize must be positive")
        self._maxsize = maxsize
        self._items = collections.deque()

        # ONE lock, TWO condition variables sharing it. This is the tuned
        # version: a put() wakes only getters (not other putters), so you
        # avoid the "thundering herd" of a single shared Condition.
        self._lock = threading.Lock()
        self._not_full = threading.Condition(self._lock)
        self._not_empty = threading.Condition(self._lock)

    def put(self, item, timeout=None):
        # Deadline computed ONCE. Passing the full `timeout` to every wait()
        # inside the loop would let a repeatedly-woken thread wait forever.
        deadline = None if timeout is None else time.monotonic() + timeout

        with self._not_full:
            while len(self._items) >= self._maxsize:   # WHILE, not if
                if deadline is None:
                    self._not_full.wait()
                else:
                    remaining = deadline - time.monotonic()
                    if remaining <= 0 or not self._not_full.wait(remaining):
                        # wait() returned False -> timed out. But re-check the
                        # predicate first: we may have been woken just in time.
                        if len(self._items) >= self._maxsize:
                            raise TimeoutError("put timed out")
                        break
            self._items.append(item)
            self._not_empty.notify()      # exactly one item -> wake one getter

    def get(self, timeout=None):
        deadline = None if timeout is None else time.monotonic() + timeout

        with self._not_empty:
            while not self._items:
                if deadline is None:
                    self._not_empty.wait()
                else:
                    remaining = deadline - time.monotonic()
                    if remaining <= 0 or not self._not_empty.wait(remaining):
                        if not self._items:
                            raise TimeoutError("get timed out")
                        break
            item = self._items.popleft()
            self._not_full.notify()       # exactly one slot -> wake one putter
            return item

    def qsize(self):
        with self._lock:
            return len(self._items)

    def __len__(self):
        return self.qsize()


# ---------------------------------------------------------------------------
# SIMPLER SINGLE-CONDITION VERSION -- correct, slightly less efficient.
# Note it MUST use notify_all(): with one condition, waiting putters and
# waiting getters share a queue, so notify() might wake the wrong kind of
# thread, which then goes straight back to sleep -> everyone hangs.
class SimpleBoundedQueue:
    def __init__(self, maxsize):
        self._maxsize = maxsize
        self._items = collections.deque()
        self._cond = threading.Condition()

    def put(self, item, timeout=None):
        with self._cond:
            if not self._cond.wait_for(
                    lambda: len(self._items) < self._maxsize, timeout):
                raise TimeoutError("put timed out")
            self._items.append(item)
            self._cond.notify_all()

    def get(self, timeout=None):
        with self._cond:
            if not self._cond.wait_for(lambda: bool(self._items), timeout):
                raise TimeoutError("get timed out")
            item = self._items.popleft()
            self._cond.notify_all()
            return item

    def qsize(self):
        with self._cond:
            return len(self._items)


# THE TWO QUESTIONS THE INTERVIEWER WILL ASK:
#
# Q: Why `while`, not `if`?
# A: wait() returning does not guarantee the predicate holds. Another thread
#    can win the lock and consume the item between the notify and your wake-up,
#    and spurious wakeups are explicitly permitted. You must re-check.
#
# Q: notify() or notify_all()?
# A: With SEPARATE conditions for not-full and not-empty, notify() is correct
#    and cheaper: one item added can satisfy exactly one getter, and every
#    thread on _not_empty wants the same thing. With a SINGLE shared condition
#    you must use notify_all(), or you can wake a putter when you meant to wake
#    a getter and deadlock.
