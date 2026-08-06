"""
Module 10 - queue.Queue: the producer/consumer workhorse.

Run:  python multithreading/examples/10_queue_producer_consumer.py

THE most useful module here. Queue is already thread-safe -- it does the locking
and the Condition waiting internally so your code has none.
"""

import itertools
import queue
import random
import threading
import time


def demo_1_basic():
    print("\n--- 1. One producer, three consumers, sentinel shutdown ---")
    q = queue.Queue(maxsize=5)          # maxsize -> BACKPRESSURE. Always set it.
    SENTINEL = object()
    results = queue.Queue()

    def producer():
        for i in range(10):
            q.put(i)                    # blocks if the queue is full
            print(f"    [producer] put {i} (qsize~{q.qsize()})")
            time.sleep(0.02)
        # One sentinel PER consumer so each one gets exactly one.
        for _ in range(3):
            q.put(SENTINEL)
        print("    [producer] done, sent 3 sentinels")

    def consumer(name):
        while True:
            item = q.get()              # blocks until something is available
            if item is SENTINEL:
                q.task_done()
                print(f"    [{name}] got sentinel, exiting")
                return
            time.sleep(random.uniform(0.05, 0.15))
            results.put(item * item)
            print(f"    [{name}] processed {item}")
            q.task_done()               # pair EVERY get() with a task_done()

    p = threading.Thread(target=producer, name="producer")
    cs = [threading.Thread(target=consumer, args=(f"consumer-{i}",)) for i in range(3)]
    p.start()
    for c in cs: c.start()
    p.join()
    for c in cs: c.join()

    got = sorted(results.queue)
    print(f"  results: {got}")
    print(f"  all 10 processed exactly once: {got == [i*i for i in range(10)]}")


def demo_2_task_done_and_join():
    print("\n--- 2. q.join(): wait for all work to be FINISHED (not just dequeued) ---")
    q = queue.Queue()
    done = []
    lock = threading.Lock()

    def worker():
        while True:
            item = q.get()              # daemon workers -> no sentinel needed here
            time.sleep(0.1)
            with lock:
                done.append(item)
            q.task_done()               # decrements the unfinished-task counter

    for _ in range(4):
        threading.Thread(target=worker, daemon=True).start()

    for i in range(12):
        q.put(i)

    t0 = time.perf_counter()
    q.join()                            # blocks until unfinished count hits 0
    print(f"  q.join() returned after {time.perf_counter() - t0:.2f}s, "
          f"{len(done)} items complete")
    print("""
  q.join() counts put()s vs task_done()s.
    - Forget task_done()  -> q.join() hangs forever.
    - Call it twice       -> ValueError('task_done() called too many times').
  Pattern: daemon workers + q.join() means you never manage worker lifetimes.""")


def demo_3_backpressure():
    print("\n--- 3. maxsize gives you backpressure (memory safety) ---")
    q = queue.Queue(maxsize=2)
    log = []
    lock = threading.Lock()

    def slow_consumer():
        for _ in range(5):
            item = q.get()
            time.sleep(0.2)             # deliberately slower than the producer
            with lock:
                log.append(f"consumed {item}")

    c = threading.Thread(target=slow_consumer)
    c.start()

    for i in range(5):
        t0 = time.perf_counter()
        q.put(i)                        # will BLOCK once 2 are queued
        waited = time.perf_counter() - t0
        with lock:
            log.append(f"put {i} (blocked {waited:.2f}s)")
    c.join()

    for line in log:
        print(f"    {line}")
    print("  The fast producer was forced to slow down to the consumer's pace.")
    print("  maxsize=0 (the default) is UNBOUNDED -- a fast producer will OOM you.")


def demo_4_nonblocking():
    print("\n--- 4. Non-blocking and timeout variants ---")
    q = queue.Queue(maxsize=2)

    try:
        q.get_nowait()                  # same as get(block=False)
    except queue.Empty:
        print("    get_nowait() on empty -> queue.Empty")

    q.put(1); q.put(2)
    try:
        q.put_nowait(3)
    except queue.Full:
        print("    put_nowait() on full  -> queue.Full")

    t0 = time.perf_counter()
    try:
        q.put(3, timeout=0.3)
    except queue.Full:
        print(f"    put(timeout=0.3) gave up after {time.perf_counter()-t0:.2f}s")

    print(f"    q.empty()={q.empty()} q.full()={q.full()} q.qsize()={q.qsize()}")
    print("  WARNING: empty()/full()/qsize() are snapshots and immediately stale.")
    print("  Never do `if not q.empty(): q.get()` -- another thread can drain it")
    print("  between the two lines. Use get_nowait() + except Empty instead.")


def demo_5_queue_flavours():
    print("\n--- 5. LifoQueue and PriorityQueue ---")

    fifo = queue.Queue()
    lifo = queue.LifoQueue()
    for i in range(4):
        fifo.put(i); lifo.put(i)
    print(f"    Queue     (FIFO): {[fifo.get() for _ in range(4)]}")
    print(f"    LifoQueue (stack): {[lifo.get() for _ in range(4)]}")

    pq = queue.PriorityQueue()
    counter = itertools.count()         # tiebreaker: keeps it stable AND avoids
                                        # comparing the payloads themselves
    for priority, task in [(3, "low"), (1, "urgent"), (2, "normal"), (1, "urgent-2")]:
        pq.put((priority, next(counter), task))

    order = [pq.get()[2] for _ in range(4)]
    print(f"    PriorityQueue    : {order}   (lowest number first)")
    print("  Always include a tiebreaker in the tuple. Without it, two items with")
    print("  equal priority make the heap compare your payload objects -> TypeError")
    print("  if they aren't orderable (e.g. dicts).")


def demo_6_graceful_shutdown():
    print("\n--- 6. Graceful shutdown that also drains cleanly ---")
    q = queue.Queue()
    stop = threading.Event()
    processed = []
    lock = threading.Lock()

    def worker(name):
        while True:
            try:
                # Short timeout so we periodically re-check the stop flag
                # instead of blocking on get() forever.
                item = q.get(timeout=0.1)
            except queue.Empty:
                if stop.is_set():
                    return              # nothing left AND told to stop -> exit
                continue
            try:
                time.sleep(0.05)
                with lock:
                    processed.append(item)
            finally:
                q.task_done()           # in finally: a crash must not hang q.join()

    workers = [threading.Thread(target=worker, args=(f"w{i}",)) for i in range(3)]
    for w in workers: w.start()

    for i in range(9):
        q.put(i)

    q.join()                            # wait for the backlog to drain
    stop.set()                          # then tell workers to exit
    for w in workers: w.join()

    print(f"    processed {len(processed)} items, workers all exited")
    print("  Order matters: q.join() FIRST (drain), then stop.set() (exit).")
    print("  Reversing it can drop queued work on the floor.")


if __name__ == "__main__":
    demo_1_basic()
    demo_2_task_done_and_join()
    demo_3_backpressure()
    demo_4_nonblocking()
    demo_5_queue_flavours()
    demo_6_graceful_shutdown()
