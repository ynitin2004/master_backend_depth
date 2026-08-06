"""
Module 6 - Semaphore: let N threads in, not just 1.

Run:  python multithreading/examples/06_semaphore.py
"""

import threading
import time

MAX_CONCURRENT = 3


def demo_1_limit_concurrency():
    print(f"\n--- 1. 8 threads, but only {MAX_CONCURRENT} allowed inside at once ---")
    sem = threading.Semaphore(MAX_CONCURRENT)

    # Just for observing -- a counter of who is currently inside.
    inside = 0
    peak = 0
    counter_lock = threading.Lock()

    def call_api(i):
        nonlocal inside, peak
        with sem:                       # acquire a slot (blocks if all 3 taken)
            with counter_lock:
                inside += 1
                peak = max(peak, inside)
                print(f"    worker {i} ENTERED   (inside now: {inside})")

            time.sleep(0.4)             # the rate-limited resource

            with counter_lock:
                inside -= 1
                print(f"    worker {i} left      (inside now: {inside})")
        # leaving the `with sem` block releases the slot for a waiting thread

    threads = [threading.Thread(target=call_api, args=(i,)) for i in range(8)]
    t0 = time.perf_counter()
    for t in threads: t.start()
    for t in threads: t.join()

    print(f"  peak concurrency: {peak} (cap was {MAX_CONCURRENT})")
    print(f"  8 tasks x 0.4s with a cap of 3 -> {time.perf_counter() - t0:.2f}s "
          f"(3 batches, not 8 x 0.4)")


def demo_2_lock_is_semaphore_1():
    print("\n--- 2. Semaphore(1) behaves like a Lock ---")
    sem = threading.Semaphore(1)
    order = []
    lock = threading.Lock()

    def critical(i):
        with sem:
            with lock:
                order.append(f"in{i}")
            time.sleep(0.05)
            with lock:
                order.append(f"out{i}")

    ts = [threading.Thread(target=critical, args=(i,)) for i in range(4)]
    for t in ts: t.start()
    for t in ts: t.join()

    print(f"  {order}")
    print("  Every 'in' is immediately followed by its own 'out' -> mutual exclusion.")
    print("  Difference: a Lock has an owner; a Semaphore is just a count, so any")
    print("  thread can release() one it never acquired.")


def demo_3_bounded_semaphore():
    print("\n--- 3. BoundedSemaphore catches over-release bugs ---")

    plain = threading.Semaphore(2)
    plain.release()                      # BUG: releasing without acquiring
    plain.release()
    print("  Semaphore(2) after 2 stray release() calls: capacity silently grew to 4.")
    print("  Your '2 concurrent connections' limit is now 4 and nothing told you.")

    bounded = threading.BoundedSemaphore(2)
    try:
        bounded.release()                # same bug...
    except ValueError as e:
        print(f"  BoundedSemaphore(2) raised instead: ValueError: {e}")
    print("  Prefer BoundedSemaphore when the count is a real resource limit.")


def demo_4_connection_pool():
    print("\n--- 4. Real use: a connection pool ---")

    class ConnectionPool:
        def __init__(self, size):
            self._sem = threading.BoundedSemaphore(size)
            self._free = [f"conn-{i}" for i in range(size)]
            self._lock = threading.Lock()

        def acquire(self, timeout=None):
            if not self._sem.acquire(timeout=timeout):
                raise TimeoutError("no connection available")
            with self._lock:
                return self._free.pop()

        def release(self, conn):
            with self._lock:
                self._free.append(conn)
            self._sem.release()

    pool = ConnectionPool(2)
    log = []
    log_lock = threading.Lock()

    def query(i):
        conn = pool.acquire()
        try:
            with log_lock:
                log.append(f"q{i} using {conn}")
            time.sleep(0.2)
        finally:
            pool.release(conn)           # ALWAYS release in finally

    ts = [threading.Thread(target=query, args=(i,)) for i in range(6)]
    for t in ts: t.start()
    for t in ts: t.join()

    for line in log:
        print(f"    {line}")
    print("  Only 2 connections ever existed; 6 queries shared them.")
    print("  Semaphore counts the slots, the list hands out the actual objects.")


if __name__ == "__main__":
    demo_1_limit_concurrency()
    demo_2_lock_is_semaphore_1()
    demo_3_bounded_semaphore()
    demo_4_connection_pool()
