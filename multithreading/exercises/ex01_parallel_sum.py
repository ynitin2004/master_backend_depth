"""
Problem 1 - Parallel sum.  (Tier 1, Modules 1-3)

Split `numbers` into n_threads chunks, sum each chunk in its own thread,
return the grand total.

Rules:
  - use raw threading.Thread, NOT a pool
  - must be correct for n_threads=1, and when len(numbers) < n_threads
  - must be correct EVERY run, not most runs

Check:  python multithreading/exercises/check.py 1
"""

import threading


def parallel_sum(numbers, n_threads=4):
    """Return sum(numbers), computed across n_threads threads."""
    # TODO: your code here.
    #
    # Hints:
    #   - slice the list into n_threads chunks
    #   - each thread needs somewhere to put its partial sum. Two safe options:
    #       (a) a pre-sized list where each thread owns exactly one index
    #       (b) a shared accumulator + a Lock
    #     Option (a) needs no lock at all -- do you see why?
    #   - start ALL threads first, then join them all. Starting and joining in
    #     the same loop makes the code sequential.
    raise NotImplementedError


if __name__ == "__main__":
    data = list(range(1, 1_000_001))
    print("expected:", sum(data))
    print("got     :", parallel_sum(data, 4))
