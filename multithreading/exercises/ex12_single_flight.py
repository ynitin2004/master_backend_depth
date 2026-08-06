"""
Problem 12 - Single-flight cache.  (Tier 3, Module 15)

get(key) returns a cached value, computing it via slow compute(key) on a miss.

Requirements:
  1. If 20 threads ask for the SAME missing key at once, compute() runs
     EXACTLY ONCE for that key. (This is "cache stampede" prevention.)
  2. Requests for DIFFERENT keys must NOT block each other. 5 distinct keys
     requested at once should take about as long as ONE compute, not five.

Requirement 2 is what makes this hard: a single global lock satisfies (1) but
violates (2).

Check:  python multithreading/exercises/check.py 12
"""

import threading
import time


class SingleFlightCache:
    def __init__(self, compute):
        self._compute = compute
        self._data = {}
        # TODO: you need TWO levels of locking.
        #   - a small "guard" lock protecting the dicts themselves
        #   - a PER-KEY lock so only threads wanting the same key serialise
        raise NotImplementedError

    def get(self, key):
        """Return the cached value for key, computing it at most once."""
        # TODO
        #   Sketch:
        #     1. fast path: under the guard, return self._data[key] if present
        #     2. get (or create) the per-key lock, under the guard
        #     3. acquire the per-key lock
        #     4. DOUBLE-CHECK the cache -- another thread may have filled it
        #        while you were waiting for the per-key lock
        #     5. call self._compute(key) with the GUARD RELEASED
        #        (holding the guard during compute would serialise every key)
        #     6. store the result under the guard
        raise NotImplementedError

    @property
    def size(self):
        raise NotImplementedError


if __name__ == "__main__":
    calls = []
    lock = threading.Lock()

    def slow_compute(key):
        with lock:
            calls.append(key)
        time.sleep(0.3)
        return f"value-{key}"

    cache = SingleFlightCache(slow_compute)

    ts = [threading.Thread(target=cache.get, args=("same",)) for _ in range(20)]
    t0 = time.perf_counter()
    for t in ts: t.start()
    for t in ts: t.join()
    print(f"20 threads, 1 key: computed {len(calls)} time(s) "
          f"in {time.perf_counter() - t0:.2f}s  (want 1 time, ~0.3s)")

    calls.clear()
    ts = [threading.Thread(target=cache.get, args=(f"k{i}",)) for i in range(5)]
    t0 = time.perf_counter()
    for t in ts: t.start()
    for t in ts: t.join()
    print(f"5 threads, 5 keys: computed {len(calls)} time(s) "
          f"in {time.perf_counter() - t0:.2f}s  (want 5 times, ~0.3s NOT 1.5s)")
