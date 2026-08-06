"""Solution 7 - Print in order (both parts)."""

import random
import threading


# ------------------------------------------------------------------- PART A
def run_in_order(first, second, third):
    """Two Events chain the three callables into a fixed order."""
    first_done = threading.Event()
    second_done = threading.Event()

    def run_first():
        first()
        first_done.set()

    def run_second():
        first_done.wait()          # gate: can't start until first() finished
        second()
        second_done.set()

    def run_third():
        second_done.wait()
        third()

    threads = [threading.Thread(target=fn)
               for fn in (run_first, run_second, run_third)]
    random.shuffle(threads)        # start order is deliberately scrambled
    for t in threads:
        t.start()
    for t in threads:
        t.join()


# ------------------------------------------------------------------- PART B
def print_numbers(n, n_threads=3):
    """Round-robin: thread i emits every number where (value-1) % n_threads == i."""
    cond = threading.Condition()
    printed = []
    state = {"next": 1}            # the next number to emit

    def worker(thread_id):
        while True:
            with cond:
                # Wait until it's my turn -- OR until we're finished, so that
                # threads parked here can still wake up and exit. Without the
                # second clause the program hangs at the end.
                cond.wait_for(
                    lambda: state["next"] > n
                    or (state["next"] - 1) % n_threads == thread_id
                )
                if state["next"] > n:
                    cond.notify_all()     # pass the "we're done" signal along
                    return
                printed.append(state["next"])
                state["next"] += 1
                cond.notify_all()         # someone else's turn now

    threads = [threading.Thread(target=worker, args=(i,)) for i in range(n_threads)]
    for t in threads: t.start()
    for t in threads: t.join()
    return printed


# THE TRAP IN PART B:
#   The obvious `cond.wait_for(lambda: turn == me)` deadlocks at the end.
#   After the last number, no thread's turn ever comes again, so every
#   remaining thread waits forever and join() never returns.
#   The predicate must ALSO be satisfiable by the termination condition, and
#   the exiting thread must notify_all() on its way out so the wake-up
#   cascades to everyone.
#
# VARIANTS OF THIS QUESTION: print odd/even from two threads, "zero-even-odd"
# (three threads printing 0,1,0,2,0,3...), FizzBuzz across four threads.
# All are the same turn-variable-plus-Condition shape.
