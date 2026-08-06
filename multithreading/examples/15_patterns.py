"""
Module 15 - Real-world patterns you will actually write.

Run:  python multithreading/examples/15_patterns.py

Each pattern here is production-shaped, not a toy.
"""

import queue
import random
import threading
import time
from concurrent.futures import ThreadPoolExecutor, as_completed


# ============================================================ 1. WORKER POOL
class WorkerPool:
    """A hand-rolled pool: queue + N workers + graceful shutdown.

    You'd normally use ThreadPoolExecutor. Build it once so you understand
    what the executor is doing for you.
    """

    def __init__(self, n_workers=4):
        self._tasks = queue.Queue()
        self._results = queue.Queue()
        self._stop = threading.Event()
        self._workers = [
            threading.Thread(target=self._loop, name=f"worker-{i}", daemon=True)
            for i in range(n_workers)
        ]
        for w in self._workers:
            w.start()

    def _loop(self):
        while True:
            try:
                fn, args = self._tasks.get(timeout=0.1)
            except queue.Empty:
                if self._stop.is_set():
                    return
                continue
            try:
                self._results.put(("ok", fn(*args)))
            except Exception as exc:                 # never let a worker die
                self._results.put(("error", exc))
            finally:
                self._tasks.task_done()              # finally: or join() hangs

    def submit(self, fn, *args):
        self._tasks.put((fn, args))

    def shutdown(self):
        self._tasks.join()                           # 1. drain the backlog
        self._stop.set()                             # 2. then tell workers to exit
        for w in self._workers:
            w.join()
        out = []
        while not self._results.empty():
            out.append(self._results.get())
        return out


def pattern_1_worker_pool():
    print("\n--- 1. Worker pool (queue + workers + graceful shutdown) ---")

    def work(n):
        time.sleep(0.05)
        if n == 3:
            raise ValueError("task 3 is cursed")
        return n * n

    pool = WorkerPool(4)
    for i in range(8):
        pool.submit(work, i)
    results = pool.shutdown()

    ok = sorted(v for status, v in results if status == "ok")
    errs = [str(v) for status, v in results if status == "error"]
    print(f"    succeeded: {ok}")
    print(f"    failed   : {errs}")
    print("    A worker that lets an exception escape DIES and your pool shrinks")
    print("    silently. Always wrap the task body in try/except.")


# ======================================================== 2. FAN-OUT / FAN-IN
def pattern_2_fan_out_fan_in():
    print("\n--- 2. Fan-out / fan-in with order preserved ---")

    def process(chunk):
        time.sleep(random.uniform(0.05, 0.2))
        return sum(chunk)

    data = list(range(100))
    chunks = [data[i:i + 20] for i in range(0, len(data), 20)]

    with ThreadPoolExecutor(max_workers=5) as pool:
        # Map future -> its INDEX so we can rebuild the original order.
        futures = {pool.submit(process, c): i for i, c in enumerate(chunks)}
        partial = [None] * len(chunks)
        for fut in as_completed(futures):
            partial[futures[fut]] = fut.result()

    print(f"    chunk sums (in original order): {partial}")
    print(f"    total = {sum(partial)}  (expected {sum(data)})")
    print("    as_completed gives completion order; the index map restores yours.")


# ================================================== 3. THREAD-SAFE COMPONENTS
class Counter:
    """The canonical thread-safe primitive."""

    def __init__(self):
        self._value = 0
        self._lock = threading.Lock()

    def increment(self, by=1):
        with self._lock:
            self._value += by
            return self._value

    def compare_and_set(self, expected, new):
        """Check AND act atomically -- this is what a bare `if` cannot do."""
        with self._lock:
            if self._value == expected:
                self._value = new
                return True
            return False

    @property
    def value(self):
        with self._lock:
            return self._value


class TTLCache:
    """Thread-safe cache where a miss is computed exactly once.

    The subtlety: we must NOT hold the lock while computing (that would
    serialise everything), but we also must not let 10 threads compute the
    same key. Solution: a per-key lock.
    """

    def __init__(self):
        self._data = {}
        self._locks = {}
        self._guard = threading.Lock()      # protects _locks only

    def _lock_for(self, key):
        with self._guard:
            return self._locks.setdefault(key, threading.Lock())

    def get_or_compute(self, key, compute):
        with self._guard:
            if key in self._data:           # fast path, no per-key lock needed
                return self._data[key]

        with self._lock_for(key):           # only threads wanting THIS key wait
            with self._guard:               # double-check after acquiring
                if key in self._data:
                    return self._data[key]
            value = compute()               # slow work, lock NOT held on _guard
            with self._guard:
                self._data[key] = value
            return value


def pattern_3_thread_safe_components():
    print("\n--- 3. Thread-safe counter and single-flight cache ---")

    c = Counter()
    with ThreadPoolExecutor(max_workers=8) as pool:
        list(pool.map(lambda _: [c.increment() for _ in range(1000)], range(8)))
    print(f"    Counter after 8x1000 increments: {c.value} (expected 8000)")
    print(f"    compare_and_set(8000, 0) -> {c.compare_and_set(8000, 0)}")
    print(f"    compare_and_set(8000, 1) -> {c.compare_and_set(8000, 1)} (already 0)")

    cache = TTLCache()
    compute_count = Counter()

    def expensive():
        compute_count.increment()
        time.sleep(0.2)
        return "EXPENSIVE_VALUE"

    with ThreadPoolExecutor(max_workers=10) as pool:
        results = list(pool.map(
            lambda _: cache.get_or_compute("k", expensive), range(10)))

    print(f"    10 threads asked for the same key; computed "
          f"{compute_count.value} time(s), all got {set(results)}")
    print("    Without the per-key lock this would compute 10 times ('cache")
    print("    stampede'). Naively locking the whole cache would serialise")
    print("    every key against every other. Per-key locks give you both.")


# ============================================================= 4. SINGLETON
def pattern_4_singleton():
    print("\n--- 4. Thread-safe lazy singleton (double-checked locking) ---")

    class Config:
        _instance = None
        _lock = threading.Lock()
        _init_count = Counter()

        @classmethod
        def get(cls):
            if cls._instance is None:            # 1st check: fast, no lock
                with cls._lock:
                    if cls._instance is None:    # 2nd check: under the lock
                        time.sleep(0.05)         # slow construction
                        cls._init_count.increment()
                        cls._instance = cls()
            return cls._instance

    with ThreadPoolExecutor(max_workers=20) as pool:
        instances = list(pool.map(lambda _: Config.get(), range(20)))

    print(f"    20 threads -> constructed {Config._init_count.value} time(s)")
    print(f"    all the same object: {len(set(map(id, instances))) == 1}")
    print("    The FIRST check avoids taking the lock on every call once it's")
    print("    built. The SECOND check is what makes it correct.")
    print("    (In real code, a module-level object or functools.cache is simpler.)")


# =========================================================== 5. RATE LIMITER
class RateLimiter:
    """Token bucket: at most `rate` operations per second, across all threads."""

    def __init__(self, rate, per=1.0):
        self._rate = rate
        self._per = per
        self._tokens = float(rate)
        self._last = time.monotonic()
        self._lock = threading.Lock()

    def acquire(self):
        while True:
            with self._lock:
                now = time.monotonic()
                # Refill proportionally to elapsed time.
                self._tokens = min(self._rate,
                                   self._tokens + (now - self._last) * self._rate / self._per)
                self._last = now
                if self._tokens >= 1:
                    self._tokens -= 1
                    return
                deficit = (1 - self._tokens) * self._per / self._rate
            time.sleep(deficit)          # sleep OUTSIDE the lock. Always.


def pattern_5_rate_limiter():
    print("\n--- 5. Rate limiter: 5 calls/sec shared by 10 threads ---")
    limiter = RateLimiter(rate=5, per=1.0)
    stamps = []
    lock = threading.Lock()

    def call_api(i):
        limiter.acquire()
        with lock:
            stamps.append(time.monotonic())

    t0 = time.monotonic()
    with ThreadPoolExecutor(max_workers=10) as pool:
        list(pool.map(call_api, range(15)))
    elapsed = time.monotonic() - t0

    print(f"    15 calls at 5/sec took {elapsed:.2f}s (5 burst + 10 throttled ~2s)")
    print(f"    max calls in any 1s window: "
          f"{max(sum(1 for s in stamps if x <= s < x + 1) for x in stamps)}")
    print("    Note `time.sleep` happens OUTSIDE the lock -- sleeping while")
    print("    holding a lock blocks every other thread for no reason.")


# ================================================ 6. TIMEOUT AND CANCELLATION
def pattern_6_timeout_and_cancellation():
    print("\n--- 6. Timeouts and REAL cancellation ---")

    # Wrong way: result(timeout) gives up waiting, work continues.
    def uninterruptible():
        time.sleep(1.0)
        return "done"

    with ThreadPoolExecutor(max_workers=1) as pool:
        f = pool.submit(uninterruptible)
        try:
            f.result(timeout=0.2)
        except TimeoutError:
            print("    result(timeout=0.2) raised -- but the task kept running,")
            print("    burning a worker slot for the full second. Not cancellation.")

    # Right way: the task cooperates.
    def interruptible(cancel_event):
        for i in range(20):
            if cancel_event.is_set():
                return f"cancelled after {i} steps"
            time.sleep(0.05)
        return "completed all 20 steps"

    cancel = threading.Event()
    with ThreadPoolExecutor(max_workers=1) as pool:
        f = pool.submit(interruptible, cancel)
        time.sleep(0.2)
        cancel.set()
        print(f"    cooperative: {f.result()}")

    print("    Rule: the ONLY real timeout is one the task itself honours --")
    print("    a cancel Event, or a timeout on the underlying call")
    print("    (requests.get(url, timeout=5), socket.settimeout, ...).")


# =============================================================== 7. RETRIES
def pattern_7_retry():
    print("\n--- 7. Retry with exponential backoff + jitter, inside a pool ---")
    attempts = {}
    lock = threading.Lock()

    def flaky(task_id):
        with lock:
            attempts[task_id] = attempts.get(task_id, 0) + 1
            n = attempts[task_id]
        if n < 3:                                   # fails twice, then works
            raise ConnectionError(f"task {task_id} attempt {n} failed")
        return f"task {task_id} ok on attempt {n}"

    def with_retry(fn, task_id, retries=4, base=0.02):
        for attempt in range(retries):
            try:
                return fn(task_id)
            except ConnectionError:
                if attempt == retries - 1:
                    raise
                # Exponential backoff + JITTER. Without jitter, every failing
                # client retries in lockstep and stampedes the recovering server.
                delay = base * (2 ** attempt) + random.uniform(0, base)
                time.sleep(delay)

    with ThreadPoolExecutor(max_workers=4) as pool:
        futures = [pool.submit(with_retry, flaky, i) for i in range(4)]
        for f in as_completed(futures):
            print(f"    {f.result()}")


if __name__ == "__main__":
    random.seed(1)
    pattern_1_worker_pool()
    pattern_2_fan_out_fan_in()
    pattern_3_thread_safe_components()
    pattern_4_singleton()
    pattern_5_rate_limiter()
    pattern_6_timeout_and_cancellation()
    pattern_7_retry()
