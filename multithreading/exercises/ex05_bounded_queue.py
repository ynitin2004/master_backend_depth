"""
Problem 5 - Bounded blocking queue, from scratch.  (Tier 2, Module 8)

*** The most commonly asked "implement a concurrency primitive" question. ***

Implement BoundedQueue using ONLY threading.Condition. No `queue` module.

  put(item)              blocks while the queue is full
  get()                  blocks while the queue is empty
  put(item, timeout=x)   raises TimeoutError if it can't put within x seconds
  get(timeout=x)         raises TimeoutError if it can't get within x seconds
  qsize()                current number of items

Must be correct with many producers AND many consumers at once.

Check:  python multithreading/exercises/check.py 5
"""

import collections
import threading


class BoundedQueue:
    def __init__(self, maxsize):
        self._maxsize = maxsize
        self._items = collections.deque()
        # TODO: one Condition is enough (it contains its own lock).
        #       Using two Conditions over ONE shared lock is the tuned version:
        #           lock = threading.Lock()
        #           self._not_full  = threading.Condition(lock)
        #           self._not_empty = threading.Condition(lock)
        #       ...so a put() only wakes getters, not other putters.
        raise NotImplementedError

    def put(self, item, timeout=None):
        # TODO
        #   with self._cond:
        #       wait while len(self._items) >= self._maxsize   <- WHILE, not if
        #       append the item
        #       notify waiters
        #
        #   For the timeout: compute a deadline ONCE up front
        #   (deadline = time.monotonic() + timeout) and pass the REMAINING time
        #   to each wait() call. Passing `timeout` fresh every loop means a
        #   thread that keeps getting woken could wait forever.
        raise NotImplementedError

    def get(self, timeout=None):
        # TODO: the mirror image of put()
        raise NotImplementedError

    def qsize(self):
        # TODO
        raise NotImplementedError


if __name__ == "__main__":
    import threading as th
    import time

    q = BoundedQueue(3)
    got = []

    def producer():
        for i in range(10):
            q.put(i)

    def consumer():
        for _ in range(10):
            got.append(q.get())
            time.sleep(0.01)

    p, c = th.Thread(target=producer), th.Thread(target=consumer)
    p.start(); c.start(); p.join(); c.join()
    print(f"got {got}  (expected 0..9 in order)")
