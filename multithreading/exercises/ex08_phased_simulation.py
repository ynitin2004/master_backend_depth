"""
Problem 8 - Barrier-based phased simulation.  (Tier 2, Module 9)

n workers each run k phases. Rules:
  - no worker may begin phase i+1 until EVERY worker has finished phase i
  - between phases, exactly ONE thread computes the aggregate for that phase
  - workers have different speeds, so you cannot rely on timing

Check:  python multithreading/exercises/check.py 8
"""

import random
import threading
import time


def run_simulation(n_workers=4, n_phases=3):
    """Return (phase_aggregates, violations).

    phase_aggregates: list of length n_phases; entry i is the sum of every
                      worker's contribution during phase i.
    violations:       list of strings describing any ordering violation your
                      code detected (should be empty).

    Each worker's contribution in phase p is simply (worker_id + 1) * (p + 1).
    """
    # TODO
    #   Hints:
    #     - threading.Barrier(n_workers)
    #     - barrier.wait() returns a unique index 0..n-1. Exactly one thread
    #       gets 0 -- make that thread the aggregator.
    #     - CAREFUL: the aggregator must finish aggregating BEFORE anyone starts
    #       the next phase. One barrier gets you "all arrived"; you need a
    #       second wait (or Barrier(action=...)) so nobody races ahead while
    #       the aggregation is still running.
    #       threading.Barrier(n, action=fn) runs fn once, automatically, while
    #       all threads are still parked. That is the clean answer.
    raise NotImplementedError


if __name__ == "__main__":
    aggregates, violations = run_simulation(4, 3)
    print("aggregates:", aggregates)
    print("expected  :", [sum((w + 1) * (p + 1) for w in range(4)) for p in range(3)])
    print("violations:", violations)
