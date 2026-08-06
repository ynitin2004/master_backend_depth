"""Solution 3 - Thread-safe counter."""

import threading


class SafeCounter:
    def __init__(self, initial=0):
        self._value = initial
        self._lock = threading.Lock()

    def increment(self, by=1):
        with self._lock:
            self._value += by
            return self._value

    def decrement(self, by=1):
        with self._lock:
            self._value -= by
            return self._value

    @property
    def value(self):
        # Even a plain read goes through the lock. On CPython an int read is
        # atomic so this is belt-and-braces, but it makes the invariant
        # explicit and it stays correct on free-threaded builds.
        with self._lock:
            return self._value

    def increment_if_below(self, limit):
        # THE POINT OF THIS EXERCISE.
        #
        # WRONG:
        #     if self.value < limit:      # <- lock released here!
        #         self.increment()        # <- another thread slipped in
        #         return True
        #     return False
        #
        # Two threads at value == limit-1 both pass the check, both increment,
        # and the counter ends at limit+1. The comparison and the mutation must
        # be inside ONE lock acquisition.
        with self._lock:
            if self._value < limit:
                self._value += 1
                return True
            return False
