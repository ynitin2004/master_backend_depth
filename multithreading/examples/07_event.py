"""
Module 7 - Event: a flag threads can wait on.

Run:  python multithreading/examples/07_event.py
"""

import threading
import time


def demo_1_starting_gate():
    print("\n--- 1. Startup gate: workers wait until config is ready ---")
    config_ready = threading.Event()
    config = {}

    def worker(i):
        print(f"    worker {i} waiting for config...")
        config_ready.wait()                 # blocks until set()
        print(f"    worker {i} GO -> using {config['url']}")

    threads = [threading.Thread(target=worker, args=(i,)) for i in range(4)]
    for t in threads: t.start()

    time.sleep(0.5)
    print("  [main] loading config...")
    config["url"] = "db://localhost"
    config_ready.set()                      # releases ALL waiters at once

    for t in threads: t.join()
    print("  set() wakes EVERY waiter -- that's the difference from a Lock.")


def demo_2_wait_returns():
    print("\n--- 2. wait() return value and timeouts ---")
    ev = threading.Event()

    print(f"  is_set() before      : {ev.is_set()}")
    t0 = time.perf_counter()
    got = ev.wait(timeout=0.3)              # nobody sets it
    print(f"  wait(0.3) -> {got}  after {time.perf_counter() - t0:.2f}s (timed out)")

    ev.set()
    t0 = time.perf_counter()
    got = ev.wait(timeout=5)                # already set -> instant
    print(f"  wait(5)   -> {got}   after {time.perf_counter() - t0:.4f}s (already set)")

    ev.clear()
    print(f"  after clear(), is_set() = {ev.is_set()}  (reusable, unlike a one-shot)")
    print("  ALWAYS check wait()'s return: False means TIMEOUT, not 'ready'.")


def demo_3_shutdown_signal():
    print("\n--- 3. Shutdown signal (the pattern you'll use most) ---")
    shutdown = threading.Event()
    counts = {}
    lock = threading.Lock()

    def poller(name, interval):
        n = 0
        # `while not shutdown.is_set()` + `shutdown.wait(interval)` instead of
        # time.sleep(interval) -> shutdown is immediate, not up to `interval` late.
        while not shutdown.is_set():
            n += 1
            if shutdown.wait(interval):     # True == we were told to stop
                break
        with lock:
            counts[name] = n
        print(f"    {name} stopped after {n} polls")

    workers = [
        threading.Thread(target=poller, args=("fast-poller", 0.1), name="fast"),
        threading.Thread(target=poller, args=("slow-poller", 5.0), name="slow"),
    ]
    for t in workers: t.start()

    time.sleep(0.45)
    print("  [main] signalling shutdown...")
    t0 = time.perf_counter()
    shutdown.set()
    for t in workers: t.join()
    print(f"  [main] everything stopped in {time.perf_counter() - t0:.3f}s")
    print("  Note the slow-poller had a 5s interval but stopped instantly,")
    print("  because it slept on the Event rather than on time.sleep().")


def demo_4_ping_pong():
    print("\n--- 4. Two Events used to alternate turns ---")
    a_turn = threading.Event()
    b_turn = threading.Event()
    log = []

    def player(name, mine, theirs, rounds):
        for _ in range(rounds):
            mine.wait()
            mine.clear()
            log.append(name)
            theirs.set()

    ta = threading.Thread(target=player, args=("ping", a_turn, b_turn, 3))
    tb = threading.Thread(target=player, args=("pong", b_turn, a_turn, 3))
    ta.start(); tb.start()
    a_turn.set()                              # kick it off
    ta.join(); tb.join()

    print(f"  {' -> '.join(log)}")
    print("  Strict alternation, guaranteed. For anything more complex than this,")
    print("  reach for a Condition (Module 8) or a Queue (Module 10) instead.")


if __name__ == "__main__":
    demo_1_starting_gate()
    demo_2_wait_returns()
    demo_3_shutdown_signal()
    demo_4_ping_pong()
