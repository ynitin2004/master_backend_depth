"""Problem 4 - Key-Value Store with TTL. Reference solution."""

import heapq
import threading
import time
from dataclasses import dataclass
from typing import Any, Callable, Optional


@dataclass
class _Entry:
    value: Any
    expires_at: Optional[float]      # monotonic; None = never

    def is_expired(self, now: float) -> bool:
        return self.expires_at is not None and self.expires_at <= now


class KVStore:
    """Lazy expiry + active sweeping. You need BOTH:

      - lazy only  -> keys nobody reads are never reclaimed (memory leak)
      - active only-> stale values are returned between sweeps (correctness)

    Knowing that is the actual point of this question.
    """

    def __init__(self, sweep_interval: float = 0.5):
        self._data: dict[str, _Entry] = {}
        self._lock = threading.RLock()

        # Min-heap of (expires_at, key) so the sweeper doesn't scan every key.
        # Entries here can be stale (key re-set or deleted) -- we validate on pop.
        self._expiry_heap: list[tuple[float, str]] = []

        # Per-key locks for get_or_set, so different keys never block each other.
        self._key_locks: dict[str, threading.Lock] = {}

        self.hits = 0
        self.misses = 0
        self.expired = 0

        self._stop = threading.Event()
        self._sweeper = threading.Thread(target=self._sweep_loop,
                                         name="kv-sweeper", daemon=True)
        self._sweep_interval = sweep_interval
        self._sweeper.start()

    # ------------------------------------------------------------- writes
    def set(self, key: str, value: Any, ttl: Optional[float] = None,
            nx: bool = False) -> bool:
        """nx=True -> set only if absent. Returns True if stored."""
        if ttl is not None and ttl <= 0:
            raise ValueError("ttl must be positive")
        now = time.monotonic()
        expires_at = None if ttl is None else now + ttl

        with self._lock:
            # nx is a check-then-act: the existence check and the write MUST
            # be one atomic step or two threads both see "absent".
            if nx:
                existing = self._data.get(key)
                if existing is not None and not existing.is_expired(now):
                    return False
            self._data[key] = _Entry(value, expires_at)
            if expires_at is not None:
                heapq.heappush(self._expiry_heap, (expires_at, key))
            return True

    def incr(self, key: str, by: int = 1) -> int:
        """Atomic read-modify-write. The reason this class exists."""
        now = time.monotonic()
        with self._lock:
            entry = self._data.get(key)
            current = 0 if entry is None or entry.is_expired(now) else entry.value
            if not isinstance(current, int):
                raise TypeError(f"value at {key!r} is not an int")
            new_value = current + by
            ttl_left = None if entry is None else entry.expires_at
            self._data[key] = _Entry(new_value, ttl_left if entry and
                                     not entry.is_expired(now) else None)
            return new_value

    def delete(self, key: str) -> bool:
        with self._lock:
            return self._data.pop(key, None) is not None

    # -------------------------------------------------------------- reads
    def get(self, key: str) -> Any:
        now = time.monotonic()
        with self._lock:
            entry = self._data.get(key)
            if entry is None:
                self.misses += 1
                return None
            # LAZY EXPIRY: an expired key is invisible immediately, without
            # waiting for the sweeper.
            if entry.is_expired(now):
                del self._data[key]
                self.expired += 1
                self.misses += 1
                return None
            self.hits += 1
            return entry.value

    def exists(self, key: str) -> bool:
        return self.get(key) is not None

    def ttl(self, key: str) -> Optional[float]:
        now = time.monotonic()
        with self._lock:
            entry = self._data.get(key)
            if entry is None or entry.is_expired(now):
                return None
            if entry.expires_at is None:
                return float("inf")
            return entry.expires_at - now

    def keys(self) -> list[str]:
        now = time.monotonic()
        with self._lock:
            return [k for k, e in self._data.items() if not e.is_expired(now)]

    def size(self) -> int:
        now = time.monotonic()
        with self._lock:
            return sum(1 for e in self._data.values() if not e.is_expired(now))

    # ------------------------------------------------------- single flight
    def get_or_set(self, key: str, factory: Callable[[], Any],
                   ttl: Optional[float] = None) -> Any:
        """factory() runs EXACTLY ONCE per key, even under 20 concurrent
        callers -- and different keys never block each other."""
        value = self.get(key)
        if value is not None:
            return value

        key_lock = self._lock_for(key)
        # Only callers wanting THIS key serialise here.
        with key_lock:
            # Double-check: the thread ahead of us probably just filled it.
            value = self.get(key)
            if value is not None:
                return value
            # factory() runs with the STORE lock released -- a slow factory
            # must not block reads of unrelated keys.
            value = factory()
            self.set(key, value, ttl)
            return value

    def _lock_for(self, key: str) -> threading.Lock:
        with self._lock:
            lock = self._key_locks.get(key)
            if lock is None:
                lock = threading.Lock()
                self._key_locks[key] = lock
            return lock

    # -------------------------------------------------------- active sweep
    def _sweep_loop(self) -> None:
        while not self._stop.is_set():
            # stop.wait(), not time.sleep() -- close() returns immediately
            # instead of waiting out a full interval.
            if self._stop.wait(self._sweep_interval):
                return
            self._sweep()

    def _sweep(self) -> int:
        """Pop due entries off the heap. O(expired), not O(all keys)."""
        now = time.monotonic()
        reclaimed = 0
        with self._lock:
            while self._expiry_heap and self._expiry_heap[0][0] <= now:
                expires_at, key = heapq.heappop(self._expiry_heap)
                entry = self._data.get(key)
                # The heap entry may be stale (key re-set with a later TTL,
                # or deleted). Validate against the real entry before removing.
                if entry is not None and entry.expires_at == expires_at:
                    del self._data[key]
                    self._key_locks.pop(key, None)
                    self.expired += 1
                    reclaimed += 1
        return reclaimed

    # -------------------------------------------------------------- admin
    def stats(self) -> dict:
        with self._lock:
            return {"hits": self.hits, "misses": self.misses,
                    "expired": self.expired, "size": self.size(),
                    "tracked": len(self._data)}

    def close(self, timeout: float = 5.0) -> None:
        self._stop.set()
        self._sweeper.join(timeout=timeout)

    def __enter__(self):
        return self

    def __exit__(self, *exc):
        self.close()


# ===========================================================================
if __name__ == "__main__":
    with KVStore(sweep_interval=0.2) as store:
        store.set("permanent", "forever")
        store.set("temp", "gone soon", ttl=0.3)
        print("get temp      :", store.get("temp"))
        print("ttl temp      :", round(store.ttl("temp"), 2))

        time.sleep(0.35)
        print("after expiry  :", store.get("temp"), "(lazy expiry: immediate)")
        print("keys          :", store.keys())

        print("\nnx semantics")
        print("  set nx (new) :", store.set("k", 1, nx=True))
        print("  set nx (dup) :", store.set("k", 2, nx=True))
        print("  value        :", store.get("k"))

        print("\natomic incr under 10 threads x 1000")
        store.set("counter", 0)
        threads = [threading.Thread(target=lambda: [store.incr("counter")
                                                    for _ in range(1000)])
                   for _ in range(10)]
        for t in threads: t.start()
        for t in threads: t.join()
        print("  counter      :", store.get("counter"), "(expected 10000)")

        print("\nsingle-flight get_or_set")
        calls = []
        calls_lock = threading.Lock()

        def expensive():
            with calls_lock:
                calls.append(1)
            time.sleep(0.2)
            return "computed"

        threads = [threading.Thread(target=lambda: store.get_or_set("hot", expensive))
                   for _ in range(20)]
        t0 = time.perf_counter()
        for t in threads: t.start()
        for t in threads: t.join()
        print(f"  20 threads, factory ran {len(calls)} time(s) "
              f"in {time.perf_counter() - t0:.2f}s")

        print("\nactive sweep reclaims memory")
        for i in range(100):
            store.set(f"tmp-{i}", i, ttl=0.1)
        print("  tracked before:", store.stats()["tracked"])
        time.sleep(0.5)
        print("  tracked after :", store.stats()["tracked"], "(sweeper reclaimed)")
        print("  stats         :", store.stats())
