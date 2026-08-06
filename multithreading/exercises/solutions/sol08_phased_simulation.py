"""Solution 8 - Barrier-based phased simulation."""

import random
import threading
import time


def run_simulation(n_workers=4, n_phases=3):
    contributions = [[0] * n_workers for _ in range(n_phases)]
    aggregates = [None] * n_phases
    violations = []
    v_lock = threading.Lock()

    # Tracks which phase each worker is currently in, so we can DETECT any
    # worker running ahead of the pack.
    phase_of = [0] * n_workers
    state_lock = threading.Lock()

    current_phase = {"p": 0}

    def aggregate():
        """Barrier action: runs ONCE, automatically, while every worker is
        still parked inside barrier.wait(). Nobody can race ahead because no
        thread is released until this returns."""
        p = current_phase["p"]
        aggregates[p] = sum(contributions[p])
        current_phase["p"] = p + 1

    barrier = threading.Barrier(n_workers, action=aggregate)

    def worker(wid):
        for p in range(n_phases):
            with state_lock:
                phase_of[wid] = p
                # Nobody may be more than one phase ahead of anyone else --
                # in fact with a barrier, all workers are always in the SAME
                # phase between rendezvous points.
                spread = max(phase_of) - min(phase_of)
                if spread > 0 and len(set(phase_of)) > 1 and spread > 1:
                    with v_lock:
                        violations.append(
                            f"worker {wid} in phase {p} while others in "
                            f"{sorted(set(phase_of))}")

            time.sleep(random.uniform(0.01, 0.05) * (wid + 1))  # uneven speeds
            contributions[p][wid] = (wid + 1) * (p + 1)

            barrier.wait()      # everyone waits; action=aggregate runs once

    threads = [threading.Thread(target=worker, args=(i,), name=f"sim-{i}")
               for i in range(n_workers)]
    for t in threads: t.start()
    for t in threads: t.join()

    return aggregates, violations


# WHY `action=` AND NOT "the thread that gets index 0 aggregates":
#
#   index = barrier.wait()
#   if index == 0:
#       aggregate()          # <-- BUG
#
#   barrier.wait() releases ALL threads at once. By the time thread 0 starts
#   aggregating, the others are already computing phase p+1 and overwriting
#   the data being aggregated.
#
#   `Barrier(n, action=fn)` runs fn while every thread is still blocked, and
#   only releases them once it returns. That is exactly the guarantee you want.
#   (The alternative is a SECOND barrier.wait() after the aggregation.)
