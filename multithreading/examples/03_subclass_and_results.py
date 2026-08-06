"""
Module 3 - Subclassing Thread, getting return values out, and exception handling.

Run:  python multithreading/examples/03_subclass_and_results.py
"""

import queue
import threading
import time


# ---------------------------------------------------------------- subclassing
class DownloadThread(threading.Thread):
    """Subclass when the thread has its own state/behaviour.

    Override run(). Still call start() -- never run() directly.
    """

    def __init__(self, url, delay=0.3):
        super().__init__(name=f"dl-{url}")   # MUST call super().__init__()
        self.url = url
        self.delay = delay
        self.result = None
        self.error = None

    def run(self):
        try:
            time.sleep(self.delay)          # pretend this is a network call
            if "bad" in self.url:
                raise ValueError(f"404 for {self.url}")
            self.result = f"<html>{self.url}</html>"
        except Exception as exc:            # capture, don't let it vanish
            self.error = exc


def demo_1_subclass():
    print("\n--- 1. Subclassing Thread and reading results off the instance ---")
    threads = [DownloadThread(u) for u in ("a.com", "b.com", "bad.com")]
    for t in threads:
        t.start()
    for t in threads:
        t.join()                       # read results ONLY after join()

    for t in threads:
        if t.error:
            print(f"  {t.url:10} FAILED: {t.error}")
        else:
            print(f"  {t.url:10} -> {t.result}")


# ------------------------------------------------------- return values vanish
def demo_2_return_is_lost():
    print("\n--- 2. TRAP: the target's return value is thrown away ---")

    def compute():
        return 42

    t = threading.Thread(target=compute)
    print(f"  t.start() returned: {t.start()!r}   <- always None")
    t.join()
    print(f"  t.join()  returned: None            <- 42 is gone forever")


# --------------------------------------------------------- collect via Queue
def demo_3_queue_results():
    print("\n--- 3. Collecting results with a Queue (thread-safe by design) ---")
    results = queue.Queue()

    def compute(n):
        time.sleep(0.1)
        results.put((n, n * n))        # Queue.put is thread-safe: no lock needed

    threads = [threading.Thread(target=compute, args=(i,)) for i in range(5)]
    for t in threads:
        t.start()
    for t in threads:
        t.join()

    collected = []
    while not results.empty():         # safe here ONLY because all writers are done
        collected.append(results.get())
    print(f"  arrival order: {collected}")
    print(f"  sorted:        {sorted(collected)}")
    print("  Note: arrival order is NOT submission order. Sort if you need order.")


# ------------------------------------------------------- mutable-arg pattern
def demo_4_shared_list_slot():
    print("\n--- 4. Writing into a pre-sized list (order preserved, no lock) ---")
    out = [None] * 5                   # each thread owns exactly ONE index...

    def compute(i):
        time.sleep(0.05)
        out[i] = i * i                 # ...so there is no overlap -> no race

    threads = [threading.Thread(target=compute, args=(i,)) for i in range(5)]
    for t in threads:
        t.start()
    for t in threads:
        t.join()
    print(f"  out = {out}   (input order preserved)")
    print("  Safe because no two threads touch the same slot.")
    print("  out.append(...) from many threads would need care instead.")


# -------------------------------------------------------- exceptions in threads
def demo_5_exceptions_vanish():
    print("\n--- 5. TRAP: exceptions in a thread do NOT reach the caller ---")

    def explode():
        raise RuntimeError("boom inside the thread")

    # Install a hook so the default traceback doesn't clutter the lesson.
    seen = []
    original = threading.excepthook
    threading.excepthook = lambda a: seen.append(a.exc_value)

    t = threading.Thread(target=explode, name="exploder")
    try:
        t.start()
        t.join()
        print("  main thread: join() returned normally. No exception raised here!")
    finally:
        threading.excepthook = original

    print(f"  threading.excepthook caught it instead: {seen[0]!r}")
    print("  Options: catch inside the thread (demo 1), install excepthook,")
    print("           or use ThreadPoolExecutor -- future.result() re-raises. (Module 12)")


if __name__ == "__main__":
    demo_1_subclass()
    demo_2_return_is_lost()
    demo_3_queue_results()
    demo_4_shared_list_slot()
    demo_5_exceptions_vanish()
