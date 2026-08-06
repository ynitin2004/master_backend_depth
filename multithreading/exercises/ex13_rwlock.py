"""
Problem 13 - Read-write lock.  (Tier 4, Module 8)

*** Classic hard interview question. ***

Implement ReadWriteLock:
  - MANY readers may hold it concurrently
  - OR exactly ONE writer, exclusively (no readers at the same time)
  - no WRITER STARVATION: once a writer is waiting, NEW readers must queue
    behind it. Otherwise a continuous stream of readers blocks the writer
    forever.

Both must work as context managers:
    with lock.read_lock():  ...
    with lock.write_lock(): ...

Check:  python multithreading/exercises/check.py 13
"""

import threading
from contextlib import contextmanager


class ReadWriteLock:
    def __init__(self):
        # TODO: you need
        #   - a Condition
        #   - a count of ACTIVE readers
        #   - a flag/count for the ACTIVE writer
        #   - a count of WAITING writers   <- this is what prevents starvation
        raise NotImplementedError

    @contextmanager
    def read_lock(self):
        # TODO
        #   acquire:
        #     with cond:
        #         wait until (no active writer) AND (no WAITING writers)
        #                                            ^^^^^^^^^^^^^^^^^^^
        #                                            the anti-starvation part
        #         readers += 1
        #   release:
        #     with cond:
        #         readers -= 1
        #         if readers == 0: cond.notify_all()
        #
        #   Use try/finally so the release happens even if the body raises.
        raise NotImplementedError

    @contextmanager
    def write_lock(self):
        # TODO
        #   acquire:
        #     with cond:
        #         waiting_writers += 1
        #         wait until readers == 0 and no active writer
        #         waiting_writers -= 1
        #         writer = True
        #   release:
        #     with cond:
        #         writer = False
        #         cond.notify_all()
        raise NotImplementedError


if __name__ == "__main__":
    import time

    lock = ReadWriteLock()
    concurrent_readers = 0
    peak = 0
    stats_lock = threading.Lock()

    def reader():
        global concurrent_readers, peak
        with lock.read_lock():
            with stats_lock:
                concurrent_readers += 1
                peak = max(peak, concurrent_readers)
            time.sleep(0.1)
            with stats_lock:
                concurrent_readers -= 1

    ts = [threading.Thread(target=reader) for _ in range(5)]
    for t in ts: t.start()
    for t in ts: t.join()
    print(f"peak concurrent readers: {peak} (should be 5, not 1)")
