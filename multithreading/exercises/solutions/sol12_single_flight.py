"""Solution 12 - Single-flight cache (cache stampede prevention)."""

import threading


class SingleFlightCache:
    def __init__(self, compute):
        self._compute = compute
        self._data = {}
        self._key_locks = {}
        # The guard protects the two dicts ONLY. It is held for microseconds
        # at a time and NEVER while computing.
        self._guard = threading.Lock()
        self.compute_calls = 0

    def _lock_for(self, key):
        with self._guard:
            # setdefault is the atomic get-or-create for the lock itself.
            return self._key_locks.setdefault(key, threading.Lock())

    def get(self, key):
        # 1. Fast path -- a hit never touches the per-key lock at all.
        with self._guard:
            if key in self._data:
                return self._data[key]

        key_lock = self._lock_for(key)

        # 2. Only threads wanting THIS key serialise here. Other keys sail past.
        with key_lock:
            # 3. DOUBLE-CHECK. While we queued for key_lock, the thread ahead
            #    of us probably computed and stored the value.
            with self._guard:
                if key in self._data:
                    return self._data[key]

            # 4. The slow call happens with the GUARD RELEASED, so requests for
            #    other keys are not blocked. Only key_lock is held.
            value = self._compute(key)

            with self._guard:
                self._data[key] = value
                self.compute_calls += 1
            return value

    @property
    def size(self):
        with self._guard:
            return len(self._data)


# THE TWO WRONG ANSWERS:
#
# 1. One global lock around everything:
#        with self._lock:
#            if key not in self._data:
#                self._data[key] = self._compute(key)
#            return self._data[key]
#    Correct (compute runs once per key) but 5 different keys take 5x as long
#    because the slow compute is inside the global lock. Fails requirement 2.
#
# 2. No lock, just a check:
#        if key not in self._data:
#            self._data[key] = self._compute(key)
#    Classic check-then-act. 20 threads all miss, all compute. That is the
#    "cache stampede" / "thundering herd" that takes down a service when a hot
#    key expires: 10,000 requests all hit the database at once.
#
# THE PER-KEY LOCK DICT GROWS FOREVER. In production, delete the key's lock
# once the value is stored, or use a bounded lock-striping scheme
# (hash(key) % 64 locks) -- fixed memory, tiny chance of unrelated keys
# sharing a lock.
