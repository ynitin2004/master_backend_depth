"""
Module 1 - Your first thread.

Run:  python multithreading/examples/01_first_thread.py

Goal: see that a thread runs your function *somewhere else*, and that the main
thread keeps going while it does.
"""

import threading
import time


def worker(name, count, delay):
    """The function each thread will run."""
    for i in range(count):
        # current_thread() tells you which thread is executing this line RIGHT NOW.
        me = threading.current_thread().name
        print(f"  [{me}] {name} step {i}")
        time.sleep(delay)
    print(f"  [{threading.current_thread().name}] {name} DONE")


def demo_1_sequential():
    print("\n--- 1. No threads: strictly one after the other ---")
    start = time.perf_counter()
    worker("A", 3, 0.3)
    worker("B", 3, 0.3)
    print(f"  took {time.perf_counter() - start:.2f}s  (0.3 * 6 = 1.8s)")


def demo_2_two_threads():
    print("\n--- 2. Two threads: they interleave and overlap ---")
    start = time.perf_counter()

    # NOTE: target=worker  (the function object), NOT target=worker(...)
    #       args must be a TUPLE. args=("A", 3, 0.3)
    t1 = threading.Thread(target=worker, args=("A", 3, 0.3), name="thread-A")
    t2 = threading.Thread(target=worker, args=("B", 3, 0.3), name="thread-B")

    t1.start()   # from here on, worker("A",...) is running elsewhere
    t2.start()

    # Without join(), main would race ahead and print the timing immediately.
    t1.join()    # wait for t1 to finish
    t2.join()    # wait for t2 to finish

    print(f"  took {time.perf_counter() - start:.2f}s  (~0.9s: they overlapped)")
    print("  ^ the sleeps happened CONCURRENTLY. That is the whole point.")


def demo_3_main_keeps_going():
    print("\n--- 3. Main thread does not wait unless you tell it to ---")
    t = threading.Thread(target=worker, args=("background", 3, 0.2), name="bg")
    t.start()
    print("  [MainThread] I started the thread and immediately got here.")
    print("  [MainThread] doing my own work...")
    time.sleep(0.1)
    print("  [MainThread] now I'll wait for it")
    t.join()
    print("  [MainThread] joined.")


def demo_4_run_vs_start():
    print("\n--- 4. TRAP: t.run() does NOT create a thread ---")

    def who():
        print(f"    executed on: {threading.current_thread().name}")

    print("  calling t.run()   ->", end=" ")
    threading.Thread(target=who, name="never-used").run()
    # ^ just a normal function call on the CURRENT thread. No thread is created.

    print("  calling t.start() ->", end=" ")
    t = threading.Thread(target=who, name="real-thread")
    t.start()    # NOW a real thread is created
    t.join()

    print("  Only start() spawns a thread. Interviewers love this one.")
    print("  (run() also consumes the Thread object -- start() after run() errors.)")


def demo_5_cannot_restart():
    print("\n--- 5. TRAP: a Thread object is single-use ---")
    t = threading.Thread(target=lambda: None)
    t.start()
    t.join()
    try:
        t.start()          # already ran -> boom
    except RuntimeError as e:
        print(f"  second start() raised RuntimeError: {e}")
    print("  Need to run it again? Build a NEW Thread object.")


def demo_6_many_threads():
    print("\n--- 6. Spawning threads in a loop (the common shape) ---")
    threads = []
    for i in range(5):
        t = threading.Thread(target=worker, args=(f"task{i}", 1, 0.1), name=f"w{i}")
        threads.append(t)
        t.start()          # start them all first...

    for t in threads:
        t.join()           # ...THEN join them all.
    print("  All 5 finished.")
    print("  If you start+join inside the same loop you get sequential code!")


if __name__ == "__main__":
    demo_1_sequential()
    demo_2_two_threads()
    demo_3_main_keeps_going()
    demo_4_run_vs_start()
    demo_5_cannot_restart()
    demo_6_many_threads()

    print("\nRun this file 2-3 times: the interleaving order CHANGES.")
    print("Never write code that depends on the order you happened to see.")
