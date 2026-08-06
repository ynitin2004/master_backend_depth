"""
Problem 7 - Print in order.  (Tier 2, Modules 7-8)

Two classic interview problems.

PART A - run_in_order(first, second, third)
    Three callables are run on three threads, STARTED IN RANDOM ORDER.
    Force them to actually execute first -> second -> third.

PART B - print_numbers(n)
    Three threads print 1..n in strict round-robin:
        thread 0 prints 1, thread 1 prints 2, thread 2 prints 3,
        thread 0 prints 4, ...
    Return the list of printed numbers. It must be [1, 2, ..., n].
    (This is the "zero-even-odd" / "FizzBuzz multithreaded" family.)

Check:  python multithreading/exercises/check.py 7
"""

import random
import threading


def run_in_order(first, second, third):
    """Run the three callables on three threads, but in the given order."""
    # TODO
    #   Hint: two Events. `second` waits on the event `first` sets, and so on.
    #   Start all three threads in a shuffled order to prove it works.
    raise NotImplementedError


def print_numbers(n, n_threads=3):
    """Print 1..n round-robin across n_threads. Return the printed sequence."""
    # TODO
    #   Hint: a Condition plus a `turn` counter.
    #     with cond:
    #         cond.wait_for(lambda: turn % n_threads == my_id or done)
    #         ... emit ...
    #         turn += 1
    #         cond.notify_all()
    #   Watch the exit condition: when the last number is emitted, every other
    #   thread is still parked in wait_for. They must be able to wake and leave,
    #   or your program hangs.
    raise NotImplementedError


if __name__ == "__main__":
    out = []
    run_in_order(lambda: out.append("first"),
                 lambda: out.append("second"),
                 lambda: out.append("third"))
    print(out)
    print(print_numbers(10))
