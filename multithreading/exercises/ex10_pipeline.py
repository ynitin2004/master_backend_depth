"""
Problem 10 - Multi-stage pipeline.  (Tier 3, Module 10)

    producer(s) --[q1]--> parser(s) --[q2]--> writer(s)

Requirements:
  - different worker counts per stage (1 producer, 4 parsers, 2 writers)
  - BOUNDED queues (backpressure)
  - every item processed exactly once
  - CLEAN SHUTDOWN: no worker left blocked, no sentinel lost, process exits

*** Shutdown is the hard part. Sentinels must CASCADE stage by stage. ***

Check:  python multithreading/exercises/check.py 10
"""

import queue
import threading
import time


def run_pipeline(n_items=100, n_parsers=4, n_writers=2, qsize=10):
    """Return the list of written records.

    Stage 1 producer : emits {"id": i, "raw": f"line-{i}"} for i in range(n_items)
    Stage 2 parser   : turns it into {"id": i, "value": i * 2}
    Stage 3 writer   : appends the record to the output list
    """
    # TODO
    #   Hints:
    #     - two bounded queues: q1 (producer->parser), q2 (parser->writer)
    #     - SENTINEL = object()
    #
    #     THE CASCADE PROBLEM:
    #       The producer sends n_parsers sentinels into q1 -- one per parser.
    #       But each parser then needs to tell the writers it is done, and there
    #       are n_writers writers, not n_parsers. You cannot have every parser
    #       push n_writers sentinels (writers would exit after the first one
    #       while other parsers are still working).
    #
    #     Two correct approaches:
    #       (a) count finished parsers with a lock; the LAST parser to finish
    #           pushes n_writers sentinels into q2
    #       (b) don't use sentinels for stage 3 at all: join the parser threads
    #           from the main thread, then push n_writers sentinels yourself
    #
    #     - the output list is shared by n_writers threads -> it needs a lock
    #       (or give each writer its own list and merge at the end)
    raise NotImplementedError


if __name__ == "__main__":
    t0 = time.perf_counter()
    records = run_pipeline(100)
    print(f"{len(records)} records in {time.perf_counter() - t0:.2f}s")
    ids = sorted(r["id"] for r in records)
    print(f"every id exactly once: {ids == list(range(100))}")
