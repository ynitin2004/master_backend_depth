"""
Module 2 - Lifecycle, join(), daemon threads, and cooperative cancellation.

Run:  python multithreading/examples/02_lifecycle_join_daemon.py
"""

import subprocess
import sys
import threading
import time


def demo_1_lifecycle():
    print("\n--- 1. Thread states ---")

    def slow():
        time.sleep(0.5)

    t = threading.Thread(target=slow, name="lifecycle-demo")
    print(f"  before start : is_alive={t.is_alive()}")
    t.start()
    print(f"  after  start : is_alive={t.is_alive()}")
    t.join()
    print(f"  after  join  : is_alive={t.is_alive()}")

    try:
        t.start()
    except RuntimeError:
        print("  a dead thread cannot be restarted (RuntimeError)")


def demo_2_introspection():
    print("\n--- 2. Who is running right now? ---")

    def report():
        cur = threading.current_thread()
        print(f"  name={cur.name!r} daemon={cur.daemon} ident={cur.ident}")

    threads = [threading.Thread(target=lambda: time.sleep(0.3), name=f"sleeper-{i}")
               for i in range(3)]
    for t in threads:
        t.start()

    report()
    print(f"  main_thread()  = {threading.main_thread().name}")
    print(f"  active_count() = {threading.active_count()}  (main + 3 sleepers)")
    print("  enumerate()    =", [t.name for t in threading.enumerate()])

    for t in threads:
        t.join()
    print(f"  after joins, active_count() = {threading.active_count()}")


def demo_3_join_timeout():
    print("\n--- 3. join(timeout) does NOT kill the thread ---")

    def long_task():
        time.sleep(1.5)
        print("  [long_task] I finished eventually (nobody was waiting)")

    t = threading.Thread(target=long_task, name="stubborn", daemon=True)
    t.start()

    t.join(timeout=0.4)
    print(f"  join(0.4) returned. is_alive={t.is_alive()}  <- still running!")
    print("  join() ALWAYS returns None. Check is_alive() to know if it finished.")
    t.join()  # now actually wait for it


def demo_4_daemon():
    print("\n--- 4. Daemon vs non-daemon at interpreter exit ---")
    print("  Running two child processes to show the difference...\n")

    # NOTE: built with str.replace, not .format() -- the child script contains
    # braces of its own that .format() would try to interpret.
    template = (
        "import threading, time\n"
        "def loop(tag):\n"
        "    for i in range(5):\n"
        "        print('    [' + tag + '] tick', i, flush=True)\n"
        "        time.sleep(0.2)\n"
        "    print('    [' + tag + '] finished all 5 ticks', flush=True)\n"
        "threading.Thread(target=loop, args=(__KIND__,), daemon=__DAEMON__).start()\n"
        "print('    main thread exits now', flush=True)\n"
    )

    for kind, daemon in (("non-daemon", False), ("daemon", True)):
        print(f"  >>> daemon={daemon}")
        script = (template.replace("__DAEMON__", str(daemon))
                          .replace("__KIND__", repr(kind)))
        out = subprocess.run(
            [sys.executable, "-c", script],
            capture_output=True, text=True, timeout=30,
        )
        print(out.stdout.rstrip())
        print()

    print("  NON-DAEMON: interpreter WAITED for it -> all 5 ticks printed.")
    print("  DAEMON:     interpreter KILLED it at exit -> ticks cut short.")
    print("  Daemon threads get no cleanup, no finally, no flush. Never give")
    print("  them files, locks, or data you care about.")


def demo_5_cooperative_cancellation():
    print("\n--- 5. There is no kill(). Use an Event. ---")

    stop = threading.Event()

    def worker():
        n = 0
        # Check the flag every loop -> the thread stops ITSELF.
        while not stop.is_set():
            n += 1
            # stop.wait(x) == sleep(x) but wakes up INSTANTLY when set().
            # Using time.sleep(0.5) here would make shutdown take up to 0.5s.
            stop.wait(0.1)
        print(f"  [worker] saw the stop flag after {n} loops, exiting cleanly")

    t = threading.Thread(target=worker, name="cancellable")
    t.start()
    time.sleep(0.55)

    print("  [main] requesting stop...")
    t0 = time.perf_counter()
    stop.set()      # ask
    t.join()        # wait for it to actually finish
    print(f"  [main] shutdown took {time.perf_counter() - t0:.3f}s (near-instant)")
    print("  This is the ONLY correct way to stop a thread in Python.")


if __name__ == "__main__":
    demo_1_lifecycle()
    demo_2_introspection()
    demo_3_join_timeout()
    demo_4_daemon()
    demo_5_cooperative_cancellation()
