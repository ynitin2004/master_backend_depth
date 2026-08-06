"""
Problem 3 - Thread-safe counter.  (Tier 1, Modules 4-5)

Implement SafeCounter so that 50 threads x 1000 operations give the exact
right answer, every time.

The interesting method is increment_if_below(limit): it is a CHECK-THEN-ACT,
so the check and the increment must be ONE atomic unit. If they aren't, the
counter can exceed the limit.

Check:  python multithreading/exercises/check.py 3
"""

import threading


class SafeCounter:
    def __init__(self, initial=0):
        # TODO: store the value and create a lock
        raise NotImplementedError

    def increment(self, by=1):
        """Add `by` and return the new value."""
        # TODO
        raise NotImplementedError

    def decrement(self, by=1):
        """Subtract `by` and return the new value."""
        # TODO
        raise NotImplementedError

    @property
    def value(self):
        """Current value."""
        # TODO -- yes, even a plain read should go through the lock.
        raise NotImplementedError

    def increment_if_below(self, limit):
        """Increment ONLY if value < limit. Return True if incremented."""
        # TODO
        #   WRONG:  if self.value < limit: self.increment()
        #           -> two threads can both pass the check at value == limit-1
        #   RIGHT:  do the comparison and the mutation inside ONE `with self._lock`
        raise NotImplementedError


if __name__ == "__main__":
    c = SafeCounter()
    ts = [threading.Thread(target=lambda: [c.increment() for _ in range(1000)])
          for _ in range(50)]
    for t in ts: t.start()
    for t in ts: t.join()
    print(f"expected 50000, got {c.value}")
