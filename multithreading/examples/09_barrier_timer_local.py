"""
Module 9 - Barrier, Timer, and threading.local().

Run:  python multithreading/examples/09_barrier_timer_local.py
"""

import random
import threading
import time


def demo_1_barrier():
    print("\n--- 1. Barrier: nobody moves until everybody arrives ---")
    N = 4
    barrier = threading.Barrier(N)
    out_lock = threading.Lock()

    def worker(i):
        for phase in range(3):
            delay = 0.1 * (i + 1)
            time.sleep(delay)                       # each worker is a different speed
            with out_lock:
                print(f"    worker {i} finished phase {phase}, waiting at barrier")

            index = barrier.wait()                  # blocks until all N arrive
            # wait() returns a unique index 0..N-1; exactly one thread gets 0,
            # which makes it the natural "do the cleanup between phases" thread.
            if index == 0:
                with out_lock:
                    print(f"  === phase {phase} complete for ALL workers ===")

    threads = [threading.Thread(target=worker, args=(i,)) for i in range(N)]
    for t in threads: t.start()
    for t in threads: t.join()
    print("  Every phase line appears only after all 4 workers reported. Lock-step.")


def demo_2_broken_barrier():
    print("\n--- 2. BrokenBarrierError: what happens when someone doesn't show up ---")
    barrier = threading.Barrier(3, timeout=0.5)     # expects 3, but only 2 arrive

    def worker(i):
        try:
            barrier.wait()
            print(f"    worker {i} passed")
        except threading.BrokenBarrierError:
            print(f"    worker {i} got BrokenBarrierError (barrier timed out)")

    ts = [threading.Thread(target=worker, args=(i,)) for i in range(2)]
    for t in ts: t.start()
    for t in ts: t.join()
    print(f"  barrier.broken = {barrier.broken}")
    print("  Good design: you get an exception instead of a silent forever-hang.")
    print("  barrier.reset() puts it back in service; abort() breaks it deliberately.")


def demo_3_timer():
    print("\n--- 3. Timer: run a function after a delay ---")

    def alarm(label):
        print(f"    [{time.strftime('%H:%M:%S')}] {label} fired")

    t1 = threading.Timer(0.5, alarm, args=("timer-A",))
    t2 = threading.Timer(2.0, alarm, args=("timer-B",))

    t1.start()
    t2.start()
    print("    both timers armed (A=0.5s, B=2.0s)")

    time.sleep(0.8)
    t2.cancel()                       # cancel before it fires
    print("    timer-B cancelled before firing")
    t1.join(); t2.join()
    print("  A Timer IS a Thread -- it has start(), join(), is_alive(), daemon.")


def demo_4_repeating_timer():
    print("\n--- 4. A repeating timer (re-arms itself) ---")
    stop = threading.Event()
    ticks = []

    def tick():
        if stop.is_set():
            return
        ticks.append(time.perf_counter())
        threading.Timer(0.15, tick).start()      # schedule the next one

    tick()
    time.sleep(0.7)
    stop.set()
    time.sleep(0.2)
    print(f"    fired {len(ticks)} times in 0.7s")
    print("  Fine for simple jobs. For anything real use sched, or a worker thread")
    print("  with `stop.wait(interval)` in a loop -- one thread instead of N.")


def demo_5_thread_local():
    print("\n--- 5. threading.local(): same name, different value per thread ---")
    ctx = threading.local()
    out_lock = threading.Lock()

    def handle_request(req_id):
        # Each thread sets its own ctx.request_id. No collision, no lock needed.
        ctx.request_id = req_id
        ctx.user = f"user-{req_id}"
        time.sleep(random.uniform(0.05, 0.2))    # deep call stack, other work...
        log_something()                          # ...and this still sees OUR values

    def log_something():
        with out_lock:
            print(f"    [{threading.current_thread().name}] "
                  f"request_id={ctx.request_id} user={ctx.user}")

    threads = [threading.Thread(target=handle_request, args=(i,), name=f"req-{i}")
               for i in range(5)]
    for t in threads: t.start()
    for t in threads: t.join()

    # The main thread never set these, so it doesn't have them at all.
    print(f"    main thread has request_id? {hasattr(ctx, 'request_id')}")
    print("""
  Why this matters: it gives you implicit per-thread context without threading
  a `request_id` parameter through 20 function signatures.
  Classic uses: per-thread DB connections/cursors, HTTP sessions, request IDs,
  and wrapping client libraries that are not thread-safe.
  Caveat: values are NOT inherited by threads you spawn, and a thread pool
  REUSES threads -- so stale values leak between tasks unless you reset them.""")


def demo_6_thread_local_pool_trap():
    print("\n--- 6. TRAP: thread-local state survives into the next pooled task ---")
    from concurrent.futures import ThreadPoolExecutor
    ctx = threading.local()

    def task(i):
        seen_before = getattr(ctx, "value", None)
        ctx.value = i
        return (i, seen_before)

    with ThreadPoolExecutor(max_workers=2) as pool:
        results = list(pool.map(task, range(6)))

    for i, seen in results:
        note = "clean" if seen is None else f"INHERITED stale value {seen}"
        print(f"    task {i}: {note}")
    print("  Pool threads are reused. Always initialise (or clear) thread-local")
    print("  state at the START of each task, never assume it's fresh.")


if __name__ == "__main__":
    demo_1_barrier()
    demo_2_broken_barrier()
    demo_3_timer()
    demo_4_repeating_timer()
    demo_5_thread_local()
    demo_6_thread_local_pool_trap()
