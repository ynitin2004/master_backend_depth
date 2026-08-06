"""Solution 10 - Multi-stage pipeline with correct cascading shutdown."""

import queue
import threading

SENTINEL = object()


def run_pipeline(n_items=100, n_parsers=4, n_writers=2, qsize=10):
    q1 = queue.Queue(maxsize=qsize)      # producer -> parsers
    q2 = queue.Queue(maxsize=qsize)      # parsers  -> writers

    output = []
    out_lock = threading.Lock()

    # ------------------------------------------------------------- stage 1
    def producer():
        for i in range(n_items):
            q1.put({"id": i, "raw": f"line-{i}"})
        # One sentinel per parser: each parser consumes exactly one and stops.
        for _ in range(n_parsers):
            q1.put(SENTINEL)

    # ------------------------------------------------------------- stage 2
    def parser():
        while True:
            item = q1.get()
            if item is SENTINEL:
                return
            q2.put({"id": item["id"], "value": item["id"] * 2})

    # ------------------------------------------------------------- stage 3
    def writer():
        while True:
            record = q2.get()
            if record is SENTINEL:
                return
            with out_lock:
                output.append(record)

    prod = threading.Thread(target=producer, name="producer")
    parsers = [threading.Thread(target=parser, name=f"parser-{i}")
               for i in range(n_parsers)]
    writers = [threading.Thread(target=writer, name=f"writer-{i}")
               for i in range(n_writers)]

    for t in [prod, *parsers, *writers]:
        t.start()

    # THE CASCADE. This is the whole exercise.
    prod.join()                      # producer finished + sent its sentinels
    for p in parsers:
        p.join()                     # ALL parsers drained q1 and exited...
    for _ in range(n_writers):       # ...so now, and only now, is q2 complete
        q2.put(SENTINEL)
    for w in writers:
        w.join()

    return output


# ---------------------------------------------------------------------------
# ALTERNATIVE: let the LAST parser to finish inject the writer sentinels.
# Useful when the main thread can't sit and join (e.g. a long-running service).
def run_pipeline_self_cascading(n_items=100, n_parsers=4, n_writers=2, qsize=10):
    q1 = queue.Queue(maxsize=qsize)
    q2 = queue.Queue(maxsize=qsize)
    output = []
    out_lock = threading.Lock()

    parsers_left = n_parsers
    counter_lock = threading.Lock()

    def producer():
        for i in range(n_items):
            q1.put({"id": i, "raw": f"line-{i}"})
        for _ in range(n_parsers):
            q1.put(SENTINEL)

    def parser():
        nonlocal parsers_left
        try:
            while True:
                item = q1.get()
                if item is SENTINEL:
                    return
                q2.put({"id": item["id"], "value": item["id"] * 2})
        finally:
            # `finally` so a crashing parser still decrements -- otherwise the
            # count never reaches zero and the writers hang forever.
            with counter_lock:
                parsers_left -= 1
                last = parsers_left == 0
            if last:
                for _ in range(n_writers):
                    q2.put(SENTINEL)

    def writer():
        while True:
            record = q2.get()
            if record is SENTINEL:
                return
            with out_lock:
                output.append(record)

    threads = ([threading.Thread(target=producer)]
               + [threading.Thread(target=parser) for _ in range(n_parsers)]
               + [threading.Thread(target=writer) for _ in range(n_writers)])
    for t in threads: t.start()
    for t in threads: t.join()
    return output


# THE THREE MISTAKES EVERYONE MAKES HERE:
#
# 1. Each parser pushes n_writers sentinels into q2.
#    -> The writers all exit after the FIRST parser finishes, while three
#       parsers are still producing. Items are silently dropped.
#
# 2. Pushing sentinels into q2 right after starting the parsers.
#    -> A writer can pull the sentinel before any real record and exit early.
#       Sentinels must go in AFTER the last real item, never before.
#
# 3. Unbounded queues.
#    -> The producer races ahead and the whole dataset sits in RAM. maxsize
#       makes the fast stage block until the slow stage catches up.
