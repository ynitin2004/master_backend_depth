"""
Module 11 - Deadlock: cause it, then cure it three ways.

Run:  python multithreading/examples/11_deadlock.py

The deadlock demo uses daemon threads + timeouts so your terminal never hangs.
"""

import threading
import time


def demo_1_classic_deadlock():
    print("\n--- 1. The classic: two locks, opposite order ---")
    lock_a = threading.Lock()
    lock_b = threading.Lock()
    progress = []

    def thread_1():
        with lock_a:
            progress.append("T1 holds A")
            time.sleep(0.1)                 # give T2 time to grab B
            progress.append("T1 wants B...")
            if lock_b.acquire(timeout=1.0):  # would block FOREVER without timeout
                progress.append("T1 got B")
                lock_b.release()
            else:
                progress.append("T1 TIMED OUT waiting for B  <-- deadlocked")

    def thread_2():
        with lock_b:
            progress.append("T2 holds B")
            time.sleep(0.1)
            progress.append("T2 wants A...")
            if lock_a.acquire(timeout=1.0):
                progress.append("T2 got A")
                lock_a.release()
            else:
                progress.append("T2 TIMED OUT waiting for A  <-- deadlocked")

    t1 = threading.Thread(target=thread_1, daemon=True)
    t2 = threading.Thread(target=thread_2, daemon=True)
    t1.start(); t2.start()
    t1.join(); t2.join()

    for line in progress:
        print(f"    {line}")
    print("""
    T1: holds A, wants B  --+
                            +-- circular wait -> neither can ever proceed
    T2: holds B, wants A  --+
    Without those timeouts this program would hang forever, with no error,
    no traceback, and 0% CPU. That is what a real deadlock looks like.""")


def demo_2_coffman():
    print("\n--- 2. The four Coffman conditions (all must hold) ---")
    print("""
    1. MUTUAL EXCLUSION  - the resource can't be shared
    2. HOLD AND WAIT     - a thread holds one lock while requesting another
    3. NO PREEMPTION     - you can't forcibly take a lock away from a thread
    4. CIRCULAR WAIT     - a cycle exists in the "waits-for" graph

    Break ANY one and deadlock becomes impossible.
    In Python you can't touch 1 or 3, so every practical fix attacks 2 or 4.""")


def demo_3_fix_lock_ordering():
    print("\n--- 3. FIX A: global lock ordering (breaks circular wait) ---")

    class Account:
        def __init__(self, aid, balance):
            self.id = aid
            self.balance = balance
            self.lock = threading.Lock()

    def transfer_BAD(src, dst, amount):
        with src.lock:                       # order depends on the ARGUMENTS
            time.sleep(0.01)
            with dst.lock:                   # -> A->B and B->A deadlock
                src.balance -= amount
                dst.balance += amount

    def transfer_GOOD(src, dst, amount):
        # Always lock in a fixed global order -- here, by account id.
        # Both threads now grab acct-0 first, so there is no cycle.
        first, second = sorted((src, dst), key=lambda a: a.id)
        with first.lock:
            time.sleep(0.01)
            with second.lock:
                src.balance -= amount
                dst.balance += amount

    for label, fn in (("transfer_BAD ", transfer_BAD), ("transfer_GOOD", transfer_GOOD)):
        a, b = Account(0, 1000), Account(1, 1000)
        t1 = threading.Thread(target=fn, args=(a, b, 100), daemon=True)
        t2 = threading.Thread(target=fn, args=(b, a, 200), daemon=True)
        t1.start(); t2.start()
        t1.join(timeout=1.5); t2.join(timeout=1.5)

        if t1.is_alive() or t2.is_alive():
            print(f"    {label}: DEADLOCKED (threads still stuck after 1.5s)")
        else:
            print(f"    {label}: completed. a={a.balance} b={b.balance} "
                  f"(total {a.balance + b.balance}, conserved)")

    print("  Sorting the locks is THE standard fix. Any consistent global order")
    print("  works -- account id, table name, even id(lock).")


def demo_4_fix_timeout_backoff():
    print("\n--- 4. FIX B: timeout + release everything + retry (breaks hold-and-wait) ---")
    lock_a, lock_b = threading.Lock(), threading.Lock()
    results = []
    lock = threading.Lock()

    def acquire_both(first, second, name):
        attempts = 0
        while True:
            attempts += 1
            first.acquire()
            if second.acquire(timeout=0.05):
                with lock:
                    results.append(f"{name} succeeded on attempt {attempts}")
                second.release(); first.release()
                return
            # Couldn't get the second lock -> DON'T sit on the first one.
            first.release()
            time.sleep(0.01 * attempts)      # backoff so both don't retry in lockstep

    t1 = threading.Thread(target=acquire_both, args=(lock_a, lock_b, "T1"), daemon=True)
    t2 = threading.Thread(target=acquire_both, args=(lock_b, lock_a, "T2"), daemon=True)
    t1.start(); t2.start()
    t1.join(timeout=3); t2.join(timeout=3)

    for r in results:
        print(f"    {r}")
    print("  Both finished despite opposite lock order, because neither HOLDS")
    print("  while waiting. Cost: wasted retries. Prefer ordering when you can.")
    print("  Without the randomised/increasing backoff this can LIVELOCK --")
    print("  both threads politely retrying forever, busy but making no progress.")


def demo_5_self_deadlock():
    print("\n--- 5. The other deadlock: one thread, one Lock ---")
    lock = threading.Lock()
    with lock:
        got = lock.acquire(timeout=0.2)
        print(f"    re-acquiring a held Lock from the same thread: {got}")
    print("  A non-reentrant Lock deadlocks against itself. Use RLock (Module 5)")
    print("  for recursive code or methods that call other locked methods.")


def demo_6_diagnosing():
    print("\n--- 6. How to diagnose a hung process ---")
    print("""
    Symptom: the program sits there, 0% CPU, no output, no traceback.

    1. faulthandler -- dumps EVERY thread's stack:
           import faulthandler; faulthandler.dump_traceback_later(10, exit=True)
       or from outside:  py-spy dump --pid <PID>

    2. threading.enumerate() -- who's still alive?
           for t in threading.enumerate(): print(t.name, t.is_alive())

    3. Read the stacks: any thread parked in `lock.acquire()` is your suspect.
       Two of them waiting on different locks = you've found your cycle.

    Prevention beats diagnosis:
      - as few locks as possible
      - a documented global lock order
      - never call out to unknown code while holding a lock
      - prefer queue.Queue / ThreadPoolExecutor over hand-rolled locking""")


if __name__ == "__main__":
    demo_1_classic_deadlock()
    demo_2_coffman()
    demo_3_fix_lock_ordering()
    demo_4_fix_timeout_backoff()
    demo_5_self_deadlock()
    demo_6_diagnosing()
