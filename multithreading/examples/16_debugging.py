"""
Module 16 - Testing and debugging threaded code.

Run:  python multithreading/examples/16_debugging.py
"""

import faulthandler
import io
import logging
import os
import sys
import tempfile
import threading
import time
from concurrent.futures import ThreadPoolExecutor


def demo_1_races_hide():
    print("\n--- 1. Why your test passed and production broke ---")

    def run_once(iterations, switch_interval):
        original = sys.getswitchinterval()
        sys.setswitchinterval(switch_interval)
        try:
            counter = 0

            def inc():
                nonlocal counter
                for _ in range(iterations):
                    counter += 1

            ts = [threading.Thread(target=inc) for _ in range(4)]
            for t in ts: t.start()
            for t in ts: t.join()
            return counter == iterations * 4
        finally:
            sys.setswitchinterval(original)

    small = sum(run_once(100, 0.005) for _ in range(20))
    print(f"    100 iterations, default interval : {small}/20 runs passed")

    big = sum(run_once(100_000, 0.000001) for _ in range(5))
    print(f"    100k iterations, tiny interval    : {big}/5 runs passed")
    print("""
    Same buggy code. The small test passes because the thread rarely gets
    preempted mid-increment. To FIND races in tests:
      - crank the iteration count up
      - sys.setswitchinterval(0.000001) to force constant switching
      - more threads than cores
      - run the test 100x in a loop, not once
      - add sleeps inside critical sections to widen the window""")


def demo_2_logging_not_print():
    print("\n--- 2. Use logging, not print ---")

    stream = io.StringIO()
    handler = logging.StreamHandler(stream)
    handler.setFormatter(logging.Formatter(
        "%(relativeCreated)6.0fms [%(threadName)-12s] %(levelname)-5s %(message)s"))
    log = logging.getLogger("demo")
    log.handlers = [handler]
    log.setLevel(logging.DEBUG)
    log.propagate = False

    def work(i):
        log.info("starting item %s", i)
        time.sleep(0.05)
        log.info("finished item %s", i)

    with ThreadPoolExecutor(max_workers=3, thread_name_prefix="job") as pool:
        list(pool.map(work, range(3)))

    for line in stream.getvalue().strip().split("\n"):
        print(f"    {line}")

    print("""
    Two reasons logging beats print here:
      1. It is thread-safe -- a log record is emitted atomically. Two threads
         print()ing can interleave INSIDE a single line and produce garbage.
      2. %(threadName)s tells you who said what. Without it a threaded log is
         unreadable. Name your threads: Thread(name=...) or thread_name_prefix.""")


def demo_3_naming():
    print("\n--- 3. Name your threads ---")

    def show():
        time.sleep(0.05)

    anon = threading.Thread(target=show)
    named = threading.Thread(target=show, name="metrics-flusher")
    anon.start(); named.start()
    print(f"    alive: {[t.name for t in threading.enumerate()]}")
    anon.join(); named.join()
    print("    'Thread-14 (show)' in a 3am stack trace tells you nothing.")
    print("    'metrics-flusher' tells you everything.")


def demo_4_excepthook():
    print("\n--- 4. threading.excepthook: catch what would vanish ---")
    caught = []

    def hook(args):
        caught.append((args.thread.name, args.exc_type.__name__, str(args.exc_value)))

    original, threading.excepthook = threading.excepthook, hook
    try:
        t = threading.Thread(target=lambda: 1 / 0, name="divider")
        t.start(); t.join()
    finally:
        threading.excepthook = original

    print(f"    caught: {caught}")
    print("    Install this at startup and log it -- otherwise a crashed thread")
    print("    just prints to stderr and your service silently loses a worker.")


def demo_5_faulthandler():
    print("\n--- 5. Diagnosing a hang with faulthandler ---")
    print("""
    Your process is stuck, 0% CPU, no output. Do this:

    A) From inside the code (arm a watchdog at startup):
           import faulthandler
           faulthandler.dump_traceback_later(30, exit=True)
       If the process is still alive in 30s, it dumps EVERY thread's stack
       and dies. Perfect for CI hangs.

    B) On demand, from outside:
           faulthandler.register(signal.SIGUSR1)     # Unix
       then `kill -USR1 <pid>` prints all stacks without killing the process.
       On Windows, use `py-spy dump --pid <PID>` instead.

    C) Right now, programmatically:""")

    def parked(ev):
        ev.wait()

    ev = threading.Event()
    t = threading.Thread(target=parked, args=(ev,), name="parked-thread", daemon=True)
    t.start()
    time.sleep(0.1)

    # faulthandler writes to a real file descriptor, so StringIO won't work.
    dump_path = os.path.join(tempfile.gettempdir(), "mt_faulthandler_demo.txt")
    with open(dump_path, "w+") as fh:
        faulthandler.dump_traceback(file=fh, all_threads=True)
        fh.seek(0)
        dump = fh.read()
    os.remove(dump_path)
    ev.set(); t.join()

    lines = [l for l in dump.split("\n") if "parked" in l or "wait" in l]
    print("      (excerpt of the dump)")
    for line in lines[:4]:
        print(f"      {line.strip()}")
    print("""
    Read it like this: any thread parked in lock.acquire() / Event.wait() /
    queue.get() is a suspect. Two threads blocked on two different locks is
    your deadlock cycle.

    Also useful:  for t in threading.enumerate(): print(t.name, t.is_alive())""")


def demo_6_testing_rules():
    print("\n--- 6. How to write tests for threaded code ---")
    print("""
    ASSERT ON INVARIANTS, NEVER ON ORDER.

      BAD   assert log == ["worker-0", "worker-1", "worker-2"]
            -> flaky forever; the order is not yours to control.

      GOOD  assert sorted(log) == ["worker-0", "worker-1", "worker-2"]
            assert counter.value == n_threads * iterations
            assert set(results) == expected_set
            assert total_in == total_out            # conservation
            assert len(connections_opened) <= pool_size

    A CHECKLIST FOR REVIEWING THREADED CODE:
      [ ] Every shared mutable object has an owner and a lock.
      [ ] Locks are always taken in the same global order.
      [ ] No I/O, sleeps, or callbacks while holding a lock.
      [ ] Every queue.get() has a matching task_done(), in a `finally`.
      [ ] Every worker's body is wrapped in try/except (a dead worker is silent).
      [ ] Every submit() has a corresponding result()/exception() check.
      [ ] Shutdown is cooperative (Event), and join()ed with a timeout.
      [ ] Daemon threads own nothing that must be flushed or closed.
      [ ] Queues have a maxsize (backpressure).
      [ ] Threads are named.

    TOOLS
      python -X dev script.py       extra runtime checks
      py-spy top / py-spy dump      no-install profiling & stack dumps
      pytest -p no:randomly -x --count=100   (pytest-repeat) shake out flakes""")


if __name__ == "__main__":
    demo_1_races_hide()
    demo_2_logging_not_print()
    demo_3_naming()
    demo_4_excepthook()
    demo_5_faulthandler()
    demo_6_testing_rules()
