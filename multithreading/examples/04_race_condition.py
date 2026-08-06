"""
Module 4 - Race conditions. See data corruption with your own eyes.

Run:  python multithreading/examples/04_race_condition.py
Run it several times -- the wrong answer is DIFFERENT every run. That is the
defining symptom of a race condition.
"""

import dis
import sys
import threading
import time

ITERATIONS = 200_000


def demo_1_lost_updates():
    print("\n--- 1. counter += 1 from two threads ---")
    counter = 0

    def increment():
        nonlocal counter
        for _ in range(ITERATIONS):
            counter += 1          # <-- NOT atomic

    t1 = threading.Thread(target=increment)
    t2 = threading.Thread(target=increment)
    t1.start(); t2.start()
    t1.join();  t2.join()

    expected = ITERATIONS * 2
    print(f"  expected : {expected}")
    print(f"  actual   : {counter}")
    print(f"  LOST     : {expected - counter} increments"
          if counter != expected else "  (got lucky this run -- run it again)")


def demo_2_why():
    print("\n--- 2. Why? Because one line is several bytecodes ---")
    src = "counter += 1"
    print(f"  Python source: {src}")
    print("  Bytecode:")
    code = compile("counter = counter + 1", "<demo>", "exec")
    for ins in dis.get_instructions(code):
        print(f"      {ins.opname:<20} {ins.argrepr}")
    print("""
  Timeline of the bug:
      Thread A: LOAD counter -> 41
      Thread B: LOAD counter -> 41       <- switch happened here
      Thread A: ADD  -> 42 ; STORE 42
      Thread B: ADD  -> 42 ; STORE 42    <- overwrites A's work
      Result: two increments, counter only went up by 1.

  A thread switch can happen between ANY two bytecodes.""")


def demo_3_amplified():
    print("\n--- 3. Amplifying the race so it fails 100% of the time ---")
    balance = 100

    def withdraw(amount):
        nonlocal balance
        if balance >= amount:            # CHECK
            time.sleep(0.01)             # a switch here is realistic (I/O, GC, anything)
            balance -= amount            # ACT

    # Both threads check "100 >= 100" -> both pass -> both withdraw.
    threads = [threading.Thread(target=withdraw, args=(100,)) for _ in range(2)]
    for t in threads: t.start()
    for t in threads: t.join()

    print(f"  Started with 100, two threads each withdrew 100 (only one should succeed)")
    print(f"  Final balance: {balance}   <- overdrawn!")
    print("  This is CHECK-THEN-ACT: the state changed between the if and the action.")
    print("  Far more common in real code than counter bugs. Think: 'if not exists: create'.")


def demo_4_check_then_act_dict():
    print("\n--- 4. The same bug in the wild: get-or-create ---")
    cache = {}
    created = []

    def get_or_create(key):
        if key not in cache:             # CHECK
            time.sleep(0.005)            # simulate a slow build
            cache[key] = object()        # ACT
            created.append(key)

    threads = [threading.Thread(target=get_or_create, args=("cfg",)) for _ in range(5)]
    for t in threads: t.start()
    for t in threads: t.join()

    print(f"  'cfg' was constructed {len(created)} times (should be 1)")
    print("  If that constructor opened a DB connection or a file, you now leak 5.")


def demo_5_what_is_atomic():
    print("\n--- 5. Some things ARE atomic under the GIL (don't rely on it) ---")
    lst, d = [], {}

    def append_many():
        for i in range(50_000):
            lst.append(i)                # single bytecode-ish -> no items lost
            d[i] = i

    ts = [threading.Thread(target=append_many) for _ in range(2)]
    for t in ts: t.start()
    for t in ts: t.join()

    print(f"  len(list) = {len(lst)} (expected 100000) -- append() didn't lose data")
    print(f"  switch interval = {sys.getswitchinterval()}s (how often threads rotate)")
    print("""
  BUT: this is a CPython implementation detail, not a language guarantee.
    - It breaks the moment you need TWO operations to be atomic together
      (e.g. `if x not in lst: lst.append(x)` -- demo 4's bug).
    - It does not hold on free-threaded (no-GIL) builds, Python 3.13+.
  Rule: if two threads share mutable state, use a lock. Module 5.""")


if __name__ == "__main__":
    demo_1_lost_updates()
    demo_2_why()
    demo_3_amplified()
    demo_4_check_then_act_dict()
    demo_5_what_is_atomic()
    print("\n>>> Run this file again. The numbers change. That's a race condition.")
