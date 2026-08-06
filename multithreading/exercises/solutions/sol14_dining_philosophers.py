"""Solution 14 - Dining philosophers, two deadlock-free solutions."""

import random
import threading
import time


def dine_ordered(n_philosophers=5, n_meals=3):
    """Solution A: global resource ordering -- breaks CIRCULAR WAIT."""
    forks = [threading.Lock() for _ in range(n_philosophers)]
    meals = [0] * n_philosophers

    def philosopher(i):
        left, right = i, (i + 1) % n_philosophers
        # THE FIX: sort the fork indices. Everyone acquires the lower-numbered
        # fork first, so philosopher 4 (forks 4 and 0) reaches for fork 0
        # first. There is no longer a cycle in the waits-for graph.
        first, second = sorted((left, right))

        for _ in range(n_meals):
            time.sleep(random.uniform(0.001, 0.005))     # thinking
            with forks[first]:
                with forks[second]:
                    meals[i] += 1                        # eating
                    time.sleep(0.001)

    threads = [threading.Thread(target=philosopher, args=(i,), name=f"phil-{i}")
               for i in range(n_philosophers)]
    for t in threads: t.start()
    for t in threads: t.join()
    return meals


def dine_limited(n_philosophers=5, n_meals=3):
    """Solution B: seat at most n-1 -- breaks HOLD-AND-WAIT."""
    forks = [threading.Lock() for _ in range(n_philosophers)]
    meals = [0] * n_philosophers
    # With at most n-1 philosophers reaching for forks, at least one of them
    # can always obtain both -> someone always makes progress.
    seats = threading.Semaphore(n_philosophers - 1)

    def philosopher(i):
        left, right = i, (i + 1) % n_philosophers
        for _ in range(n_meals):
            time.sleep(random.uniform(0.001, 0.005))
            with seats:                     # take a seat at the table
                with forks[left]:
                    with forks[right]:
                        meals[i] += 1
                        time.sleep(0.001)

    threads = [threading.Thread(target=philosopher, args=(i,))
               for i in range(n_philosophers)]
    for t in threads: t.start()
    for t in threads: t.join()
    return meals


def dine_asymmetric(n_philosophers=5, n_meals=3):
    """Solution C: odd philosophers reverse their order -- breaks the symmetry."""
    forks = [threading.Lock() for _ in range(n_philosophers)]
    meals = [0] * n_philosophers

    def philosopher(i):
        left, right = i, (i + 1) % n_philosophers
        # Even -> left then right. Odd -> right then left.
        first, second = (left, right) if i % 2 == 0 else (right, left)
        for _ in range(n_meals):
            time.sleep(random.uniform(0.001, 0.005))
            with forks[first]:
                with forks[second]:
                    meals[i] += 1
                    time.sleep(0.001)

    threads = [threading.Thread(target=philosopher, args=(i,))
               for i in range(n_philosophers)]
    for t in threads: t.start()
    for t in threads: t.join()
    return meals


def dine_deadlocking(n_philosophers=5, n_meals=1, timeout=2.0):
    """The NAIVE version, for contrast. Returns (meals, deadlocked: bool).

    Uses daemon threads so it can't hang the test suite.
    """
    forks = [threading.Lock() for _ in range(n_philosophers)]
    meals = [0] * n_philosophers
    barrier = threading.Barrier(n_philosophers)   # force the worst case

    def philosopher(i):
        left, right = i, (i + 1) % n_philosophers
        for _ in range(n_meals):
            barrier.wait()                # everyone reaches at the same instant
            forks[left].acquire()         # <- everyone grabs their left fork
            time.sleep(0.01)
            if not forks[right].acquire(timeout=timeout):
                forks[left].release()
                return                    # gave up: this IS the deadlock
            meals[i] += 1
            forks[right].release()
            forks[left].release()

    threads = [threading.Thread(target=philosopher, args=(i,), daemon=True)
               for i in range(n_philosophers)]
    for t in threads: t.start()
    for t in threads: t.join(timeout=timeout + 1)
    return meals, sum(meals) < n_philosophers * n_meals


# MAPPING THE FIXES TO THE COFFMAN CONDITIONS (Module 11):
#
#   A) resource ordering  -> breaks CIRCULAR WAIT
#   B) limiting semaphore -> breaks HOLD-AND-WAIT (only n-1 can hold at once)
#   C) asymmetry          -> breaks CIRCULAR WAIT (a different way)
#
# You cannot break MUTUAL EXCLUSION (a fork is genuinely exclusive) or
# NO PREEMPTION (Python won't let you steal a lock), so every real fix in
# Python targets condition 2 or 4. Say that in the interview.
#
# STARVATION is separate from deadlock: solution A is deadlock-free but a
# slow philosopher could in principle be repeatedly beaten to the forks.
# The semaphore version distributes access more evenly.
