"""Solution 15 - Thread-safe LRU cache."""

import threading
from collections import OrderedDict


class LRUCache:
    def __init__(self, capacity):
        if capacity <= 0:
            raise ValueError("capacity must be positive")
        self.capacity = capacity
        self._data = OrderedDict()       # ordered oldest -> newest
        self._lock = threading.Lock()
        self._hits = 0
        self._misses = 0
        self._evictions = 0

    def get(self, key):
        with self._lock:
            if key not in self._data:
                self._misses += 1
                return None
            # A HIT counts as a use -> promote to most-recently-used.
            # This move MUST be in the same lock acquisition as the lookup,
            # or two threads interleave and the ordering is corrupted.
            self._data.move_to_end(key)
            self._hits += 1
            return self._data[key]

    def put(self, key, value):
        with self._lock:
            if key in self._data:
                self._data[key] = value
                self._data.move_to_end(key)
                return
            self._data[key] = value
            # The size check and the eviction are ATOMIC together. If they
            # weren't, two threads inserting into a full cache would both see
            # "there's room" and the cache would exceed capacity.
            if len(self._data) > self.capacity:
                self._data.popitem(last=False)    # pop the OLDEST
                self._evictions += 1

    def __len__(self):
        with self._lock:
            return len(self._data)

    def __contains__(self, key):
        with self._lock:
            return key in self._data

    @property
    def stats(self):
        with self._lock:
            return {"hits": self._hits,
                    "misses": self._misses,
                    "evictions": self._evictions}


# ---------------------------------------------------------------------------
# ANSWERS TO THE THINKING POINTS
#
# WHERE DOES THE LOCK GO?
#   Around the ENTIRE body of every public method. Not just the mutation:
#   `get` looks like a read but it MUTATES the ordering (move_to_end) and the
#   hit counter, so it is a writer too. This is the classic mistake -- people
#   leave `get` unlocked because "reads are safe".
#
# WHY NOT A PLAIN dict + A SEPARATE "RECENTLY USED" LIST?
#   Two containers means two mutations that must stay in sync. Any interleaving
#   between them leaves the cache and the order list disagreeing about what
#   exists -- you evict a key that isn't there, or leak one that is. You'd need
#   a lock anyway, and OrderedDict already gives you O(1) move_to_end and
#   O(1) popitem(last=False). A list would also make "move to end" O(n).
#
# CAN YOU DO BETTER THAN ONE GLOBAL LOCK?
#   Yes -- SHARDING. Keep N independent LRUCache shards and route by
#   hash(key) % N. Threads touching different shards never contend, so you get
#   roughly Nx the throughput. The cost: the eviction policy becomes per-shard,
#   so it's approximately-LRU rather than strictly-LRU globally. That is the
#   trade real caches (Guava, Caffeine, memcached) all make.
#
#   You cannot use functools.lru_cache here: it has no eviction visibility,
#   no stats you control, and no put(). It IS thread-safe for the common case
#   though -- and worth naming as the "don't reinvent this" answer when the
#   requirement is just memoisation.
