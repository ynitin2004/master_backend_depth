"""
Problem 15 - Thread-safe LRU cache.  (Tier 4, Modules 5, 15)

Implement LRUCache(capacity), thread-safe:
  get(key)        -> value or None. A HIT counts as a use (most-recent now).
  put(key, value) -> stores; evicts the least-recently-used if full.
  stats           -> {"hits": n, "misses": n, "evictions": n}

Requirements:
  - len(cache) must NEVER exceed capacity, under ANY interleaving
  - eviction order must be correct under concurrency
  - the stats counters must be exact

Thinking point: OrderedDict.move_to_end makes the single-threaded version four
lines. Where does the lock go? Why can't you use a plain dict + a separate
"recently used" list?

Check:  python multithreading/exercises/check.py 15
"""

import threading
from collections import OrderedDict


class LRUCache:
    def __init__(self, capacity):
        self.capacity = capacity
        self._data = OrderedDict()
        # TODO: one lock. Every public method's ENTIRE body goes inside it.
        raise NotImplementedError

    def get(self, key):
        # TODO
        #   with self._lock:
        #       miss -> misses += 1, return None
        #       hit  -> self._data.move_to_end(key), hits += 1, return value
        #
        #   The move_to_end MUST be inside the same lock as the lookup, or two
        #   threads can interleave and corrupt the ordering.
        raise NotImplementedError

    def put(self, key, value):
        # TODO
        #   with self._lock:
        #       if key exists: update + move_to_end
        #       else: insert; if len > capacity: popitem(last=False) + evictions += 1
        #
        #   The size check and the eviction must be atomic together, or two
        #   threads inserting at capacity both see "room for one more".
        raise NotImplementedError

    def __len__(self):
        raise NotImplementedError

    @property
    def stats(self):
        raise NotImplementedError


if __name__ == "__main__":
    c = LRUCache(3)
    for i in range(3):
        c.put(f"k{i}", i)
    c.get("k0")            # k0 is now most-recently-used
    c.put("k3", 3)         # should evict k1 (least recently used)
    print("k0 present (should be 0)   :", c.get("k0"))
    print("k1 evicted (should be None):", c.get("k1"))
    print("stats:", c.stats)
