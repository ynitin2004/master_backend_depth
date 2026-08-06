"""
Module 12 - ThreadPoolExecutor and futures. THE production API.

Run:  python multithreading/examples/12_thread_pool_executor.py
"""

import random
import threading
import time
from concurrent.futures import (
    ALL_COMPLETED,
    FIRST_COMPLETED,
    ThreadPoolExecutor,
    as_completed,
    wait,
)


def fake_fetch(url, delay=None):
    """Pretend to hit the network."""
    time.sleep(delay if delay is not None else random.uniform(0.1, 0.5))
    if "bad" in url:
        raise ConnectionError(f"could not reach {url}")
    return f"{len(url) * 100} bytes from {url}"


def demo_1_submit_and_result():
    print("\n--- 1. submit() -> Future -> result() ---")
    with ThreadPoolExecutor(max_workers=3) as pool:
        future = pool.submit(fake_fetch, "example.com", 0.3)
        print(f"    submit() returned immediately: {type(future).__name__}")
        print(f"    done() right away? {future.done()}")
        value = future.result()                 # blocks until ready
        print(f"    result(): {value}")
        print(f"    done() now? {future.done()}")


def demo_2_map_vs_as_completed():
    print("\n--- 2. map() (input order) vs as_completed() (finish order) ---")
    urls = ["slow.com", "fast.io", "medium.net", "quick.dev"]
    delays = {"slow.com": 0.6, "fast.io": 0.1, "medium.net": 0.35, "quick.dev": 0.15}

    print("  pool.map -- results come back in SUBMISSION order:")
    with ThreadPoolExecutor(max_workers=4) as pool:
        for url, res in zip(urls, pool.map(lambda u: fake_fetch(u, delays[u]), urls)):
            print(f"    {url:12} -> {res}")

    print("  as_completed -- results come back as they FINISH:")
    with ThreadPoolExecutor(max_workers=4) as pool:
        futures = {pool.submit(fake_fetch, u, delays[u]): u for u in urls}
        for fut in as_completed(futures):
            print(f"    {futures[fut]:12} -> {fut.result()}")

    print("  as_completed lets you show progress and react to the first result.")
    print("  The dict {future: url} is the idiom for remembering what a future was for.")


def demo_3_exceptions():
    print("\n--- 3. Exceptions: raised at result(), NOT at submit() ---")
    urls = ["good.com", "bad.com", "also-good.com", "bad-too.com"]

    with ThreadPoolExecutor(max_workers=4) as pool:
        futures = {pool.submit(fake_fetch, u, 0.1): u for u in urls}
        print("    all submitted, no exception yet...")

        for fut in as_completed(futures):
            url = futures[fut]
            try:
                print(f"    {url:14} OK   {fut.result()}")
            except ConnectionError as e:        # re-raised HERE, in the caller
                print(f"    {url:14} FAIL {e}")

    print("""
  This is the single biggest reason to use a pool over raw threads:
  exceptions come back to you instead of vanishing.

  THE GOTCHA: if you submit() and never call result()/exception(), the error
  is silently swallowed. Fire-and-forget with a pool hides your bugs.""")

    # exception() gives you the error without raising
    with ThreadPoolExecutor() as pool:
        f = pool.submit(fake_fetch, "bad.com", 0.05)
        print(f"    future.exception() -> {f.exception()!r} (returns, doesn't raise)")


def demo_4_map_fails_fast():
    print("\n--- 4. TRAP: map() raises on the first error and you lose the rest ---")
    urls = ["a.com", "bad.com", "c.com", "d.com"]

    with ThreadPoolExecutor(max_workers=4) as pool:
        try:
            for res in pool.map(lambda u: fake_fetch(u, 0.05), urls):
                print(f"    got {res}")
        except ConnectionError as e:
            print(f"    map() blew up: {e}")
    print("  Results after the failing one are unreachable, even though they")
    print("  completed fine. Use submit + as_completed when partial failure is normal.")


def demo_5_pool_sizing():
    print("\n--- 5. Pool size vs wall-clock, for I/O-bound work ---")
    n_tasks = 16
    task_time = 0.1

    for workers in (1, 2, 4, 8, 16):
        with ThreadPoolExecutor(max_workers=workers) as pool:
            t0 = time.perf_counter()
            list(pool.map(lambda _: time.sleep(task_time), range(n_tasks)))
            elapsed = time.perf_counter() - t0
        ideal = n_tasks * task_time / workers
        print(f"    {workers:2} workers: {elapsed:.2f}s  (ideal {ideal:.2f}s)")

    print(f"  {n_tasks} tasks x {task_time}s each. More workers -> near-linear gain")
    print("  because the threads are all just WAITING (GIL released).")
    print("  Sizing: I/O-bound -> tune to the remote service's limits (32/64 is fine).")
    print("          CPU-bound -> a thread pool won't help; use ProcessPoolExecutor.")
    print("  Default max_workers = min(32, os.cpu_count() + 4).")


def demo_6_wait_and_cancel():
    print("\n--- 6. wait(), timeouts, and cancellation ---")

    with ThreadPoolExecutor(max_workers=2) as pool:
        futures = [pool.submit(fake_fetch, f"host{i}.com", 0.3 * (i + 1))
                   for i in range(4)]

        done, not_done = wait(futures, timeout=0.5, return_when=FIRST_COMPLETED)
        print(f"    wait(FIRST_COMPLETED): {len(done)} done, {len(not_done)} pending")

        # cancel() only works on futures that have NOT started yet.
        cancelled = [f.cancel() for f in futures]
        print(f"    cancel() results: {cancelled}")
        print("    -> True only for queued tasks; a RUNNING task cannot be cancelled.")

        done, not_done = wait(futures, timeout=5, return_when=ALL_COMPLETED)
        print(f"    finally: {len(done)} settled")

    print("\n    result(timeout=...) raises TimeoutError but does NOT stop the work:")
    with ThreadPoolExecutor(max_workers=1) as pool:
        f = pool.submit(fake_fetch, "slow.com", 1.0)
        try:
            f.result(timeout=0.2)
        except TimeoutError:
            print("      caught TimeoutError -- but the thread is STILL fetching.")
        print(f"      eventual result: {f.result()}")

    print("""
    There is no real 'kill this task' in Python. If you need genuine timeouts,
    the task itself must check an Event, or the underlying call must take its
    own timeout (e.g. requests.get(url, timeout=5)).""")


def demo_7_initializer():
    print("\n--- 7. initializer: per-thread setup done once ---")
    local = threading.local()
    made = []
    lock = threading.Lock()

    def setup():
        # Runs ONCE per worker thread, before any task.
        local.conn = f"conn-for-{threading.current_thread().name}"
        with lock:
            made.append(local.conn)

    def task(i):
        return f"task {i} used {local.conn}"

    with ThreadPoolExecutor(max_workers=3, thread_name_prefix="db",
                            initializer=setup) as pool:
        for r in pool.map(task, range(6)):
            print(f"    {r}")

    print(f"    connections created: {len(made)} (for 6 tasks, because 3 threads)")
    print("  Perfect for expensive per-thread resources: DB connections, sessions.")


if __name__ == "__main__":
    random.seed(0)
    demo_1_submit_and_result()
    demo_2_map_vs_as_completed()
    demo_3_exceptions()
    demo_4_map_fails_fast()
    demo_5_pool_sizing()
    demo_6_wait_and_cancel()
    demo_7_initializer()
