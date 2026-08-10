"""Problem 1 - Rate Limiter. Reference solution.

Single file for easy review. In a real round, split into
models.py / strategies.py / service.py as the skeleton does.
"""

import threading
import time
from abc import ABC, abstractmethod
from collections import deque
from typing import Callable, Optional


class RateLimiter(ABC):
    """The interface. The problem said 'different algorithms' -- that is the
    interviewer telling you to write an ABC."""

    @abstractmethod
    def allow(self, key: str) -> bool:
        """Non-blocking. True if this request is permitted."""


# ===========================================================================
class TokenBucketLimiter(RateLimiter):
    """Burst up to `capacity`, refilling `refill_rate` tokens per `per` seconds.

    Best default: allows short bursts (which real traffic has) while bounding
    the sustained rate.
    """

    def __init__(self, capacity: float, refill_rate: float, per: float = 1.0):
        if capacity <= 0 or refill_rate <= 0 or per <= 0:
            raise ValueError("capacity, refill_rate and per must be positive")
        self._capacity = float(capacity)
        self._refill_rate = float(refill_rate)
        self._per = float(per)
        # Per-key state, so one noisy client can't affect another.
        self._state: dict[str, list] = {}          # key -> [tokens, last_refill]
        self._lock = threading.Lock()

    def allow(self, key: str) -> bool:
        now = time.monotonic()
        with self._lock:
            # The whole method is one critical section: reading the tokens,
            # refilling, comparing and decrementing is a read-modify-write.
            # Split it and two threads both see the last token.
            state = self._state.get(key)
            if state is None:
                state = [self._capacity, now]
                self._state[key] = state

            tokens, last = state
            tokens = min(self._capacity,
                         tokens + (now - last) * self._refill_rate / self._per)
            state[1] = now

            if tokens >= 1:
                state[0] = tokens - 1
                return True
            state[0] = tokens
            return False

    def last_seen(self, key: str) -> Optional[float]:
        with self._lock:
            state = self._state.get(key)
            return None if state is None else state[1]

    def forget(self, key: str) -> bool:
        with self._lock:
            return self._state.pop(key, None) is not None


# ===========================================================================
class FixedWindowLimiter(RateLimiter):
    """At most `limit` requests per fixed `window`-second bucket.

    Cheapest option: O(1) memory per key. Its flaw is the BOUNDARY BURST --
    `limit` requests at 0:59 and `limit` more at 1:01 means 2*limit inside one
    second. Name that flaw before the interviewer does.
    """

    def __init__(self, limit: int, window: float):
        if limit <= 0 or window <= 0:
            raise ValueError("limit and window must be positive")
        self._limit = limit
        self._window = float(window)
        self._state: dict[str, list] = {}          # key -> [window_start, count]
        self._lock = threading.Lock()

    def allow(self, key: str) -> bool:
        now = time.monotonic()
        bucket = int(now // self._window)
        with self._lock:
            state = self._state.get(key)
            if state is None or state[0] != bucket:
                state = [bucket, 0]
                self._state[key] = state
            if state[1] < self._limit:
                state[1] += 1
                return True
            return False

    def last_seen(self, key: str) -> Optional[float]:
        with self._lock:
            state = self._state.get(key)
            return None if state is None else state[0] * self._window

    def forget(self, key: str) -> bool:
        with self._lock:
            return self._state.pop(key, None) is not None


# ===========================================================================
class SlidingWindowLogLimiter(RateLimiter):
    """Exact sliding window: keeps a timestamp per request.

    No boundary burst -- at most `limit` in ANY window-second interval.
    Cost: O(limit) memory per key. That is the trade-off to state out loud.
    """

    def __init__(self, limit: int, window: float):
        if limit <= 0 or window <= 0:
            raise ValueError("limit and window must be positive")
        self._limit = limit
        self._window = float(window)
        self._log: dict[str, deque] = {}
        self._lock = threading.Lock()

    def allow(self, key: str) -> bool:
        now = time.monotonic()
        cutoff = now - self._window
        with self._lock:
            log = self._log.get(key)
            if log is None:
                log = deque()
                self._log[key] = log

            while log and log[0] <= cutoff:        # evict timestamps that aged out
                log.popleft()

            if len(log) < self._limit:
                log.append(now)
                return True
            return False

    def last_seen(self, key: str) -> Optional[float]:
        with self._lock:
            log = self._log.get(key)
            return log[-1] if log else None

    def forget(self, key: str) -> bool:
        with self._lock:
            return self._log.pop(key, None) is not None


# ===========================================================================
class RateLimiterService:
    """Routes each key to its own limiter, created lazily by `factory`.

    Per-key limiter instances (rather than one limiter handling all keys)
    keeps unrelated clients from contending on the same lock.
    """

    def __init__(self, factory: Callable[[], RateLimiter]):
        self._factory = factory
        self._limiters: dict[str, RateLimiter] = {}
        self._last_seen: dict[str, float] = {}
        self._lock = threading.RLock()
        self._allowed = 0
        self._denied = 0

    def allow(self, key: str) -> bool:
        limiter = self._limiter_for(key)
        permitted = limiter.allow(key)

        with self._lock:
            self._last_seen[key] = time.monotonic()
            if permitted:
                self._allowed += 1
            else:
                self._denied += 1
        return permitted

    def _limiter_for(self, key: str) -> RateLimiter:
        # Fast path: an existing key never takes the write lock path.
        with self._lock:
            limiter = self._limiters.get(key)
            if limiter is not None:
                return limiter
            # Check-then-act, inside ONE acquisition -- otherwise two threads
            # both build a limiter and one client silently gets double quota.
            limiter = self._factory()
            self._limiters[key] = limiter
            return limiter

    def evict_idle(self, older_than: float) -> int:
        """Reclaim state for keys unseen for `older_than` seconds.

        Without this, a per-key limiter is an unbounded memory leak keyed by
        user id. Interviewers ask about it; having it already written is free
        credit.
        """
        cutoff = time.monotonic() - older_than
        with self._lock:
            stale = [k for k, seen in self._last_seen.items() if seen < cutoff]
            for key in stale:
                self._limiters.pop(key, None)
                self._last_seen.pop(key, None)
            return len(stale)

    def stats(self) -> dict:
        with self._lock:
            return {"keys": len(self._limiters),
                    "allowed": self._allowed,
                    "denied": self._denied}


# ===========================================================================
if __name__ == "__main__":
    print("token bucket: capacity 5, refill 5/s")
    bucket = TokenBucketLimiter(capacity=5, refill_rate=5, per=1.0)
    print("  burst of 8 ->", [bucket.allow("user-1") for _ in range(8)])
    print("  other key  ->", [bucket.allow("user-2") for _ in range(3)])
    time.sleep(0.45)
    print("  after 0.45s->", [bucket.allow("user-1") for _ in range(3)])

    print("\nfixed window: 3 per 0.5s")
    fixed = FixedWindowLimiter(limit=3, window=0.5)
    print("  burst of 5 ->", [fixed.allow("u") for _ in range(5)])

    print("\nsliding log: 3 per 0.5s")
    sliding = SlidingWindowLogLimiter(limit=3, window=0.5)
    print("  burst of 5 ->", [sliding.allow("u") for _ in range(5)])
    time.sleep(0.55)
    print("  after 0.55s->", [sliding.allow("u") for _ in range(3)])

    print("\nservice")
    service = RateLimiterService(lambda: TokenBucketLimiter(2, 2))
    for key in ("a", "a", "a", "b"):
        print(f"  allow({key}) -> {service.allow(key)}")
    print("  stats:", service.stats())
