"""
Problem 14 - Dining philosophers.  (Tier 4, Module 11)

5 philosophers around a table, 5 forks between them. Each needs BOTH
neighbouring forks to eat. The naive "pick up left, then right" deadlocks:
everyone grabs their left fork at once and nobody can ever get a right one.

Make all n philosophers eat `n_meals` times, with NO deadlock and NO starvation.

Implement it TWO different ways:
  A) resource ordering -- always acquire the lower-numbered fork first
  B) a limiting semaphore (at most n-1 seated) OR the asymmetric solution
     (odd philosophers take left first, even take right first)

Check:  python multithreading/exercises/check.py 14
"""

import threading
import time


def dine_ordered(n_philosophers=5, n_meals=3):
    """Solution A: global resource ordering. Return meals_eaten list."""
    # TODO
    #   Each philosopher i uses forks i and (i+1) % n.
    #   Instead of always taking `left` then `right`, take
    #       first, second = sorted((left_index, right_index))
    #   Now philosopher 4 (forks 4 and 0) takes fork 0 FIRST, which breaks the
    #   circular wait -- there is no longer a cycle in the waits-for graph.
    raise NotImplementedError


def dine_limited(n_philosophers=5, n_meals=3):
    """Solution B: semaphore limits how many may try at once. Return meals list."""
    # TODO
    #   threading.Semaphore(n_philosophers - 1)
    #   With at most 4 of 5 philosophers reaching for forks, at least one can
    #   always get both -> hold-and-wait is broken, so no deadlock.
    #
    #   (The asymmetric variant is equally valid: odd-numbered philosophers
    #   take their right fork first. Same effect -- it breaks the symmetry
    #   that creates the cycle.)
    raise NotImplementedError


if __name__ == "__main__":
    for name, fn in (("ordered", dine_ordered), ("limited", dine_limited)):
        t0 = time.perf_counter()
        meals = fn(5, 3)
        print(f"{name:8}: {meals} in {time.perf_counter() - t0:.2f}s "
              f"(all should be 3)")
