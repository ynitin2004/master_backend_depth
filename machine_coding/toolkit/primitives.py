"""
Thread-safe building blocks worth having in muscle memory.

Every machine coding problem is some combination of these. If you can type
them without thinking, you buy back 20 minutes of the round.

Run:  python machine_coding/toolkit/primitives.py     (self-test)

DO NOT copy this whole file into an interview. Copy the two or three pieces
the problem actually needs. Unused abstractions read as padding.
"""

import itertools
import threading
import time
import uuid
from abc import ABC, abstractmethod
from collections import OrderedDict, defaultdict
from concurrent.futures import ThreadPoolExecutor
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Callable, Generic, Optional, TypeVar

T = TypeVar("T")


# ===========================================================================
# 1. IDs -- you need these in literally every problem
# ===========================================================================
class IdGenerator:
    """Monotonic, thread-safe, human-readable ids: 'task-1', 'task-2', ...

    Prefer this over uuid4 in a demo: readable output makes your demo easy
    for the interviewer to follow.
    """

    def __init__(self, prefix: str = "id"):
        self._prefix = prefix
        self._counter = itertools.count(1)   # itertools.count IS thread-safe
        self._lock = threading.Lock()

    def next(self) -> str:
        with self._lock:
            return f"{self._prefix}-{next(self._counter)}"

    @staticmethod
    def uuid() -> str:
        return str(uuid.uuid4())


# ===========================================================================
# 2. SafeCounter -- metrics, capacity checks, stats
# ===========================================================================
class SafeCounter:
    def __init__(self, initial: int = 0):
        self._value = initial
        self._lock = threading.Lock()

    def increment(self, by: int = 1) -> int:
        with self._lock:
            self._value += by
            return self._value

    def decrement(self, by: int = 1) -> int:
        with self._lock:
            self._value -= by
            return self._value

    def increment_if_below(self, limit: int) -> bool:
        """Check AND act atomically -- the whole reason this class exists."""
        with self._lock:
            if self._value < limit:
                self._value += 1
                return True
            return False

    @property
    def value(self) -> int:
        with self._lock:
            return self._value


# ===========================================================================
# 3. ThreadSafeStore -- the shape of nearly every "repository" you'll write
# ===========================================================================
class ThreadSafeStore(Generic[T]):
    """One lock, owned by the class. Callers never see it.

    RLock so that methods may call each other (get_or_create -> get).
    """

    def __init__(self):
        self._items: dict[str, T] = {}
        self._lock = threading.RLock()

    def put(self, key: str, item: T) -> None:
        with self._lock:
            self._items[key] = item

    def get(self, key: str) -> Optional[T]:
        with self._lock:
            return self._items.get(key)

    def delete(self, key: str) -> bool:
        with self._lock:
            return self._items.pop(key, None) is not None

    def get_or_create(self, key: str, factory: Callable[[], T]) -> T:
        # Check-then-act, done inside ONE lock acquisition. Say this out loud.
        with self._lock:
            if key not in self._items:
                self._items[key] = factory()
            return self._items[key]

    def update(self, key: str, mutator: Callable[[T], None]) -> bool:
        """Read-modify-write under the lock -- never expose the object and let
        the caller mutate it outside."""
        with self._lock:
            item = self._items.get(key)
            if item is None:
                return False
            mutator(item)
            return True

    def all(self) -> list[T]:
        with self._lock:
            return list(self._items.values())    # a COPY, not the live view

    def __len__(self) -> int:
        with self._lock:
            return len(self._items)

    def __contains__(self, key: str) -> bool:
        with self._lock:
            return key in self._items


# ===========================================================================
# 4. WorkerPool -- consume from a queue, shut down cleanly
# ===========================================================================
class WorkerPool:
    """Bounded queue + N workers + cooperative shutdown.

    Use ThreadPoolExecutor if you just need "run these callables". Use this
    when the problem wants an explicit long-lived worker pool you control
    (schedulers, brokers, pipelines).
    """

    def __init__(self, n_workers: int = 4, queue_size: int = 100,
                 handler: Optional[Callable[[Any], None]] = None):
        import queue as _queue
        self._queue = _queue.Queue(maxsize=queue_size)   # maxsize = backpressure
        self._Empty = _queue.Empty
        self._handler = handler
        self._stop = threading.Event()
        self._workers = [
            threading.Thread(target=self._run, name=f"worker-{i}", daemon=True)
            for i in range(n_workers)
        ]
        self._started = False

    def start(self) -> None:
        if self._started:
            return
        self._started = True
        for w in self._workers:
            w.start()

    def submit(self, item: Any, timeout: Optional[float] = None) -> None:
        if self._stop.is_set():
            raise RuntimeError("pool is shutting down")
        self._queue.put(item, timeout=timeout)

    def _run(self) -> None:
        while True:
            try:
                # Short timeout so we re-check the stop flag instead of
                # blocking on get() forever.
                item = self._queue.get(timeout=0.1)
            except self._Empty:
                if self._stop.is_set():
                    return
                continue
            try:
                if self._handler:
                    self._handler(item)
            except Exception:
                # A worker that lets an exception escape DIES, and your pool
                # silently shrinks. Always swallow (and log) here.
                pass
            finally:
                self._queue.task_done()   # finally: or join() hangs on a crash

    def shutdown(self, wait: bool = True, timeout: float = 5.0) -> None:
        if wait:
            self._queue.join()            # drain the backlog FIRST...
        self._stop.set()                  # ...then tell workers to exit
        for w in self._workers:
            w.join(timeout=timeout)       # ALWAYS with a timeout

    def __enter__(self):
        self.start()
        return self

    def __exit__(self, *exc):
        self.shutdown()


# ===========================================================================
# 5. TokenBucket -- rate limiting, throttling, quotas
# ===========================================================================
class TokenBucket:
    """`rate` operations per `per` seconds. `capacity` is the allowed burst."""

    def __init__(self, rate: float, per: float = 1.0,
                 capacity: Optional[float] = None):
        self._rate = float(rate)
        self._per = float(per)
        self._capacity = float(capacity if capacity is not None else rate)
        self._tokens = self._capacity
        self._last = time.monotonic()
        self._lock = threading.Lock()

    def try_acquire(self, tokens: float = 1.0) -> bool:
        """Non-blocking. Returns False instead of waiting."""
        with self._lock:
            self._refill()
            if self._tokens >= tokens:
                self._tokens -= tokens
                return True
            return False

    def acquire(self, tokens: float = 1.0) -> None:
        """Blocking. Waits until tokens are available."""
        while True:
            with self._lock:
                self._refill()
                if self._tokens >= tokens:
                    self._tokens -= tokens
                    return
                wait = (tokens - self._tokens) * self._per / self._rate
            time.sleep(wait)      # OUTSIDE the lock. Always. Say this out loud.

    def _refill(self) -> None:
        """Caller must hold the lock."""
        now = time.monotonic()
        elapsed = now - self._last
        self._tokens = min(self._capacity,
                           self._tokens + elapsed * self._rate / self._per)
        self._last = now


# ===========================================================================
# 6. LRUCache -- eviction, capacity bounds, stats
# ===========================================================================
class LRUCache(Generic[T]):
    def __init__(self, capacity: int):
        if capacity <= 0:
            raise ValueError("capacity must be positive")
        self.capacity = capacity
        self._data: OrderedDict[str, T] = OrderedDict()
        self._lock = threading.Lock()
        self.hits = 0
        self.misses = 0
        self.evictions = 0

    def get(self, key: str) -> Optional[T]:
        with self._lock:
            if key not in self._data:
                self.misses += 1
                return None
            self._data.move_to_end(key)      # a HIT counts as a use
            self.hits += 1
            return self._data[key]

    def put(self, key: str, value: T) -> None:
        with self._lock:
            if key in self._data:
                self._data[key] = value
                self._data.move_to_end(key)
                return
            self._data[key] = value
            # Size check and eviction ATOMIC together, or two threads both
            # see "there's room" and you exceed capacity.
            if len(self._data) > self.capacity:
                self._data.popitem(last=False)
                self.evictions += 1

    def __len__(self) -> int:
        with self._lock:
            return len(self._data)


# ===========================================================================
# 7. ReadWriteLock -- read-heavy state (writer-preferring)
# ===========================================================================
class ReadWriteLock:
    """Many readers OR one writer. Writers are not starved.

    Only reach for this if reads VASTLY outnumber writes AND the critical
    section is long. For short sections a plain Lock is faster. Say that.
    """

    def __init__(self):
        self._cond = threading.Condition()
        self._readers = 0
        self._writer = False
        self._waiting_writers = 0        # <- the anti-starvation counter

    class _Ctx:
        def __init__(self, acquire, release):
            self._acquire, self._release = acquire, release

        def __enter__(self):
            self._acquire()
            return self

        def __exit__(self, *exc):
            self._release()

    def read_lock(self):
        return self._Ctx(self._acquire_read, self._release_read)

    def write_lock(self):
        return self._Ctx(self._acquire_write, self._release_write)

    def _acquire_read(self):
        with self._cond:
            # `not waiting_writers` is what stops a stream of readers from
            # starving a writer forever.
            self._cond.wait_for(
                lambda: not self._writer and self._waiting_writers == 0)
            self._readers += 1

    def _release_read(self):
        with self._cond:
            self._readers -= 1
            if self._readers == 0:
                self._cond.notify_all()

    def _acquire_write(self):
        with self._cond:
            self._waiting_writers += 1
            try:
                self._cond.wait_for(
                    lambda: not self._writer and self._readers == 0)
                self._writer = True
            finally:
                self._waiting_writers -= 1

    def _release_write(self):
        with self._cond:
            self._writer = False
            self._cond.notify_all()


# ===========================================================================
# 8. Observer / EventBus -- notifications, hooks, pub-sub
# ===========================================================================
class EventBus:
    """Subscribers registered per topic. Callbacks invoked OUTSIDE the lock."""

    def __init__(self):
        self._subscribers: dict[str, list[Callable]] = defaultdict(list)
        self._lock = threading.RLock()

    def subscribe(self, topic: str, callback: Callable) -> None:
        with self._lock:
            self._subscribers[topic].append(callback)

    def unsubscribe(self, topic: str, callback: Callable) -> bool:
        with self._lock:
            try:
                self._subscribers[topic].remove(callback)
                return True
            except ValueError:
                return False

    def publish(self, topic: str, payload: Any) -> int:
        # Copy the subscriber list under the lock, then RELEASE it before
        # invoking callbacks. Never hold a lock while calling unknown code --
        # it can block, raise, or re-enter your own API and deadlock.
        with self._lock:
            listeners = list(self._subscribers.get(topic, ()))

        delivered = 0
        for callback in listeners:
            try:
                callback(payload)
                delivered += 1
            except Exception:
                pass          # one bad subscriber must not break the others
        return delivered


# ===========================================================================
# 9. RetryPolicy -- an interface, because they always ask for variation
# ===========================================================================
class RetryPolicy(ABC):
    @abstractmethod
    def should_retry(self, attempt: int) -> bool: ...

    @abstractmethod
    def delay_for(self, attempt: int) -> float: ...


class NoRetry(RetryPolicy):
    def should_retry(self, attempt: int) -> bool:
        return False

    def delay_for(self, attempt: int) -> float:
        return 0.0


class ExponentialBackoff(RetryPolicy):
    def __init__(self, max_attempts: int = 3, base: float = 0.1,
                 factor: float = 2.0, jitter: float = 0.1):
        self.max_attempts = max_attempts
        self.base = base
        self.factor = factor
        self.jitter = jitter

    def should_retry(self, attempt: int) -> bool:
        return attempt < self.max_attempts

    def delay_for(self, attempt: int) -> float:
        import random
        # Jitter matters: without it every failing client retries in lockstep
        # and stampedes the recovering service.
        return self.base * (self.factor ** attempt) + random.uniform(0, self.jitter)


# ===========================================================================
# Self-test
# ===========================================================================
def _selftest():
    print("primitives self-test")

    ids = IdGenerator("task")
    got = [ids.next() for _ in range(3)]
    assert got == ["task-1", "task-2", "task-3"], got
    print("  IdGenerator        ok")

    counter = SafeCounter()
    threads = [threading.Thread(target=lambda: [counter.increment()
                                                for _ in range(1000)])
               for _ in range(10)]
    for t in threads: t.start()
    for t in threads: t.join()
    assert counter.value == 10_000, counter.value
    assert counter.increment_if_below(10_000) is False
    print("  SafeCounter        ok")

    store: ThreadSafeStore[int] = ThreadSafeStore()
    created = SafeCounter()

    def make():
        created.increment()
        return 42

    with ThreadPoolExecutor(max_workers=10) as pool:
        results = list(pool.map(lambda _: store.get_or_create("k", make), range(10)))
    assert results == [42] * 10
    assert created.value == 1, f"get_or_create raced: {created.value}"
    print("  ThreadSafeStore    ok")

    processed = SafeCounter()
    with WorkerPool(4, handler=lambda item: processed.increment()) as pool:
        for i in range(50):
            pool.submit(i)
    assert processed.value == 50, processed.value
    print("  WorkerPool         ok")

    bucket = TokenBucket(rate=5, per=1.0)
    allowed = sum(bucket.try_acquire() for _ in range(10))
    assert allowed == 5, allowed
    print("  TokenBucket        ok")

    cache: LRUCache[int] = LRUCache(3)
    for i in range(3):
        cache.put(f"k{i}", i)
    cache.get("k0")
    cache.put("k3", 3)
    assert cache.get("k1") is None, "k1 should have been evicted"
    assert cache.get("k0") == 0
    assert len(cache) == 3
    print("  LRUCache           ok")

    rw = ReadWriteLock()
    peak = SafeCounter()
    current = SafeCounter()

    def reader():
        with rw.read_lock():
            n = current.increment()
            if n > peak.value:
                peak.increment(n - peak.value)
            time.sleep(0.05)
            current.decrement()

    threads = [threading.Thread(target=reader) for _ in range(5)]
    for t in threads: t.start()
    for t in threads: t.join()
    assert peak.value >= 4, f"readers did not overlap: {peak.value}"
    print("  ReadWriteLock      ok")

    bus = EventBus()
    seen = []
    bus.subscribe("orders", seen.append)
    bus.subscribe("orders", lambda p: (_ for _ in ()).throw(RuntimeError("bad")))
    delivered = bus.publish("orders", {"id": 1})
    assert seen == [{"id": 1}] and delivered == 1
    print("  EventBus           ok")

    policy = ExponentialBackoff(max_attempts=3, base=0.1, jitter=0)
    assert policy.should_retry(2) and not policy.should_retry(3)
    assert 0.4 - 1e-9 <= policy.delay_for(2) <= 0.4 + 0.1
    print("  RetryPolicy        ok")

    print("\nall primitives pass")


if __name__ == "__main__":
    _selftest()
