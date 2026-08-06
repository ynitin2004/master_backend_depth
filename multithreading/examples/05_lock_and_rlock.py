"""
Module 5 - Lock and RLock: fixing the race from Module 4.

Run:  python multithreading/examples/05_lock_and_rlock.py
"""

import threading
import time

ITERATIONS = 200_000


def demo_1_lock_fixes_it():
    print("\n--- 1. The same counter, now with a Lock ---")
    counter = 0
    lock = threading.Lock()

    def increment():
        nonlocal counter
        for _ in range(ITERATIONS):
            with lock:            # only one thread inside this block at a time
                counter += 1      # <- the CRITICAL SECTION

    t1 = threading.Thread(target=increment)
    t2 = threading.Thread(target=increment)
    start = time.perf_counter()
    t1.start(); t2.start()
    t1.join();  t2.join()
    elapsed = time.perf_counter() - start

    print(f"  expected {ITERATIONS * 2}, got {counter}  "
          f"{'CORRECT' if counter == ITERATIONS * 2 else 'WRONG'}")
    print(f"  took {elapsed:.3f}s -- locks cost time. That's the trade.")


def demo_2_with_vs_manual():
    print("\n--- 2. `with lock:` vs manual acquire/release ---")
    lock = threading.Lock()

    # GOOD -- released even if the body raises
    with lock:
        pass

    # Equivalent, but you must not forget the finally:
    lock.acquire()
    try:
        pass
    finally:
        lock.release()

    print("  Both are equivalent. Always use `with` --")
    print("  a missing release() on an exception path hangs your program forever.")

    # A lock that is never released:
    stuck = threading.Lock()
    stuck.acquire()
    got = stuck.acquire(timeout=0.2)     # second acquire from the SAME thread
    print(f"  acquiring a held Lock with timeout=0.2 -> {got} (gave up, no hang)")
    print(f"  acquire(blocking=False) -> {stuck.acquire(blocking=False)} (instant no)")
    stuck.release()


def demo_3_lock_is_not_reentrant():
    print("\n--- 3. TRAP: Lock deadlocks against ITSELF ---")
    lock = threading.Lock()

    def outer():
        with lock:
            return inner()   # a locked method calling another locked method

    def inner():
        # We already hold `lock`. Asking for it again blocks forever.
        got = lock.acquire(timeout=0.3)   # timeout only so this demo terminates
        if got:
            lock.release()
        return got

    print(f"  nested acquire on a Lock succeeded? {outer()}")
    print("  -> It blocked. Without the timeout this is a permanent self-deadlock.")


def demo_4_rlock():
    print("\n--- 4. RLock: the same thread may re-acquire ---")
    rlock = threading.RLock()

    def outer():
        with rlock:
            print("    outer holds the RLock")
            inner()

    def inner():
        with rlock:          # same thread -> allowed, just bumps a counter
            print("    inner acquired it AGAIN, no deadlock")

    outer()
    print("  RLock counts acquisitions; you must release the same number of times.")
    print("  Use it for recursive functions and locked-method-calls-locked-method.")


def demo_5_a_thread_safe_class():
    print("\n--- 5. The standard shape: a class that owns its lock ---")

    class BankAccount:
        def __init__(self, balance=0):
            self._balance = balance
            self._lock = threading.RLock()   # RLock: methods may call each other

        def deposit(self, amount):
            with self._lock:
                self._balance += amount

        def withdraw(self, amount):
            with self._lock:                 # check AND act inside one lock
                if self._balance < amount:
                    return False
                self._balance -= amount
                return True

        def transfer_to(self, other, amount):
            # Calls withdraw() which re-acquires self._lock -> needs RLock.
            with self._lock:
                if self.withdraw(amount):
                    other.deposit(amount)
                    return True
                return False

        @property
        def balance(self):
            with self._lock:
                return self._balance

    acct = BankAccount(1000)

    def hammer():
        for _ in range(1000):
            acct.deposit(10)
            acct.withdraw(10)

    ts = [threading.Thread(target=hammer) for _ in range(8)]
    for t in ts: t.start()
    for t in ts: t.join()

    print(f"  balance after 8 threads x 1000 deposit/withdraw pairs: {acct.balance}")
    print("  Expected 1000. The lock lives INSIDE the object -- callers can't forget it.")


def demo_6_granularity():
    print("\n--- 6. Lock granularity: hold it as briefly as possible ---")
    lock = threading.Lock()
    total = 0

    def slow_bad():
        nonlocal total
        with lock:
            time.sleep(0.05)          # expensive work INSIDE the lock
            total += 1

    def slow_good():
        nonlocal total
        time.sleep(0.05)              # expensive work OUTSIDE
        with lock:
            total += 1                # only the mutation is protected

    for label, fn in (("work inside lock ", slow_bad), ("work outside lock", slow_good)):
        total = 0
        ts = [threading.Thread(target=fn) for _ in range(8)]
        t0 = time.perf_counter()
        for t in ts: t.start()
        for t in ts: t.join()
        print(f"  {label}: {time.perf_counter() - t0:.2f}s (total={total})")

    print("  Same result, but the first one serialised everything.")
    print("  NEVER do I/O, sleep, or call unknown code while holding a lock.")


if __name__ == "__main__":
    demo_1_lock_fixes_it()
    demo_2_with_vs_manual()
    demo_3_lock_is_not_reentrant()
    demo_4_rlock()
    demo_5_a_thread_safe_class()
    demo_6_granularity()
