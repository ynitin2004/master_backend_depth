"""Problem 3 - Connection Pool. Reference solution."""

import threading
import time
from contextlib import contextmanager
from typing import Any, Callable, Optional


class PoolError(Exception): ...
class PoolTimeoutError(PoolError): ...
class PoolClosedError(PoolError): ...


class _Slot:
    """An idle connection plus when it went idle (for reaping)."""
    __slots__ = ("conn", "idle_since")

    def __init__(self, conn: Any):
        self.conn = conn
        self.idle_since = time.monotonic()


class ConnectionPool:
    def __init__(self, factory: Callable[[], Any], min_size: int = 0,
                 max_size: int = 10, timeout: float = 5.0,
                 max_idle_time: Optional[float] = None,
                 validator: Optional[Callable[[Any], bool]] = None,
                 closer: Optional[Callable[[Any], None]] = None):
        if max_size <= 0:
            raise ValueError("max_size must be positive")
        if min_size < 0 or min_size > max_size:
            raise ValueError("min_size must be between 0 and max_size")

        self._factory = factory
        self._min_size = min_size
        self._max_size = max_size
        self._default_timeout = timeout
        self._max_idle_time = max_idle_time
        self._validator = validator
        self._closer = closer

        self._idle: list[_Slot] = []
        self._in_use: set[int] = set()      # id(conn) of checked-out connections
        self._total = 0                     # idle + in_use + reserved-but-not-yet-built
        self._created = 0                   # lifetime counter, for stats
        self._closed = False

        # ONE Condition guards everything. Waiters block on it and are woken
        # by release() -- no polling, no busy-wait.
        self._cond = threading.Condition()

        for _ in range(min_size):
            self._idle.append(_Slot(self._build()))

        self._reaper = None
        if max_idle_time is not None:
            self._reaper = threading.Thread(target=self._reap_loop,
                                            name="pool-reaper", daemon=True)
            self._reaper.start()

    # ------------------------------------------------------------ acquire
    def acquire(self, timeout: Optional[float] = None) -> Any:
        timeout = self._default_timeout if timeout is None else timeout
        # Deadline computed ONCE. Passing a fresh `timeout` to each wait()
        # would let a repeatedly-woken thread wait far longer than asked.
        deadline = None if timeout is None else time.monotonic() + timeout

        while True:
            with self._cond:
                if self._closed:
                    raise PoolClosedError("pool is closed")

                # 1. Reuse an idle connection.
                while self._idle:
                    slot = self._idle.pop()
                    if self._is_valid(slot.conn):
                        self._in_use.add(id(slot.conn))
                        return slot.conn
                    # Invalid -> discard it and free the capacity slot.
                    self._discard_locked(slot.conn)

                # 2. Room to grow? RESERVE the slot under the lock.
                #    This is the check-then-act the whole problem is about:
                #    incrementing _total here is what stops two threads both
                #    seeing "room for one more" and blowing past max_size.
                if self._total < self._max_size:
                    self._total += 1
                    reserved = True
                else:
                    reserved = False

                if not reserved:
                    # 3. Exhausted -- wait to be woken by a release().
                    remaining = (None if deadline is None
                                 else deadline - time.monotonic())
                    if remaining is not None and remaining <= 0:
                        raise PoolTimeoutError(
                            f"no connection available within {timeout}s")
                    self._cond.wait(remaining)
                    continue

            # 4. Build OUTSIDE the lock -- creating a connection is slow I/O
            #    and holding the lock would serialise every other caller.
            try:
                conn = self._build_unlocked()
            except Exception:
                # Creation failed: give the reserved slot back, or the pool
                # permanently believes it is one connection larger than it is.
                with self._cond:
                    self._total -= 1
                    self._cond.notify()
                raise

            with self._cond:
                self._in_use.add(id(conn))
                return conn

    # ------------------------------------------------------------ release
    def release(self, conn: Any) -> None:
        with self._cond:
            if id(conn) not in self._in_use:
                return                       # double release / foreign object
            self._in_use.discard(id(conn))

            if self._closed:
                self._discard_locked(conn)
            else:
                self._idle.append(_Slot(conn))
            self._cond.notify()              # wake ONE waiter -- one slot freed

    @contextmanager
    def connection(self, timeout: Optional[float] = None):
        conn = self.acquire(timeout)
        try:
            yield conn
        finally:
            self.release(conn)               # finally: released even on raise

    # -------------------------------------------------------------- admin
    def stats(self) -> dict:
        with self._cond:
            return {"in_use": len(self._in_use),
                    "idle": len(self._idle),
                    "total": self._total,
                    "created": self._created,
                    "max_size": self._max_size}

    def close(self, timeout: float = 5.0) -> None:
        with self._cond:
            if self._closed:
                return
            self._closed = True
            for slot in self._idle:
                self._close_conn(slot.conn)
            self._total -= len(self._idle)
            self._idle.clear()
            self._cond.notify_all()          # release every blocked acquirer
        if self._reaper is not None:
            self._reaper.join(timeout=timeout)

    def __enter__(self):
        return self

    def __exit__(self, *exc):
        self.close()

    # ----------------------------------------------------------- internal
    def _reap_loop(self) -> None:
        """Close connections idle longer than max_idle_time, never below min_size."""
        while True:
            with self._cond:
                if self._closed:
                    return
                self._cond.wait(timeout=min(0.1, self._max_idle_time or 0.1))
                if self._closed:
                    return

                cutoff = time.monotonic() - self._max_idle_time
                keep, reap = [], []
                for slot in self._idle:
                    surplus = len(self._idle) - len(reap) > self._min_size
                    if slot.idle_since < cutoff and surplus:
                        reap.append(slot)
                    else:
                        keep.append(slot)
                self._idle = keep
                for slot in reap:
                    self._discard_locked(slot.conn)

    def _is_valid(self, conn: Any) -> bool:
        if self._validator is None:
            return True
        try:
            return bool(self._validator(conn))
        except Exception:
            return False

    def _build(self) -> Any:
        conn = self._factory()
        self._total += 1
        self._created += 1
        return conn

    def _build_unlocked(self) -> Any:
        conn = self._factory()               # _total already reserved
        with self._cond:
            self._created += 1
        return conn

    def _discard_locked(self, conn: Any) -> None:
        """Caller holds the lock. Close it and free its capacity slot."""
        self._close_conn(conn)
        self._total -= 1
        self._cond.notify()

    def _close_conn(self, conn: Any) -> None:
        try:
            if self._closer is not None:
                self._closer(conn)
            elif hasattr(conn, "close"):
                conn.close()
        except Exception:
            pass


# ===========================================================================
if __name__ == "__main__":
    import itertools

    counter = itertools.count(1)

    class FakeConnection:
        def __init__(self):
            self.id = f"conn-{next(counter)}"
            self.open = True
            time.sleep(0.05)          # connections are expensive to create

        def close(self):
            self.open = False

        def __repr__(self):
            return self.id

    pool = ConnectionPool(FakeConnection, min_size=2, max_size=3, timeout=1.0)
    print("after warmup:", pool.stats())

    with pool.connection() as conn:
        print("borrowed    :", conn, pool.stats())
    print("returned    :", pool.stats())

    held = [pool.acquire() for _ in range(3)]
    print("all 3 out   :", pool.stats())
    try:
        pool.acquire(timeout=0.2)
    except PoolTimeoutError as exc:
        print("4th acquire :", type(exc).__name__, "-", exc)
    for conn in held:
        pool.release(conn)

    results = []

    def worker():
        with pool.connection(timeout=5) as conn:
            time.sleep(0.05)
            results.append(conn.id)

    threads = [threading.Thread(target=worker) for _ in range(20)]
    for t in threads: t.start()
    for t in threads: t.join()

    print(f"\n20 threads  : {len(results)} completed")
    print(f"distinct conns used: {len(set(results))} (max_size was 3)")
    print("final stats :", pool.stats())
    pool.close()
