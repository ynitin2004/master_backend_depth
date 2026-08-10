"""Created at minute 12 (as stubs), fleshed out as features landed.

This is what the interviewer runs. Sectioned output so every feature is
VISIBLE rather than merely present.

Run:  python demo.py
"""

import threading
import time

from scheduler import (
    ExponentialBackoff,
    NoRetry,
    Priority,
    Scheduler,
    TaskStatus,
)
from scheduler.exceptions import TaskNotCancellableError


def section(title):
    print(f"\n{'=' * 64}\n  {title}\n{'=' * 64}")


# ---------------------------------------------------------------- sample tasks
def add(a, b):
    time.sleep(0.05)
    return a + b


def slow_job(label, seconds=0.2):
    time.sleep(seconds)
    return f"{label} done"


def always_fails():
    raise ConnectionError("upstream unavailable")


_attempts = {"n": 0}
_attempts_lock = threading.Lock()


def flaky():
    """Fails twice, then succeeds -- shows retries actually working."""
    with _attempts_lock:
        _attempts["n"] += 1
        n = _attempts["n"]
    if n < 3:
        raise ConnectionError(f"attempt {n} failed")
    return f"succeeded on attempt {n}"


def main():
    # ---------------------------------------------------------------- P0
    section("1. Submit and execute concurrently")
    with Scheduler(n_workers=4, retry_policy=NoRetry()) as sched:
        ids = [sched.submit(add, i, i, name=f"add-{i}") for i in range(5)]
        results = [sched.get_result(tid, timeout=5) for tid in ids]
        print(f"  submitted 5 tasks to 4 workers")
        print(f"  results: {results}")

        t0 = time.perf_counter()
        slow_ids = [sched.submit(slow_job, f"job{i}", 0.2) for i in range(4)]
        for tid in slow_ids:
            sched.get_result(tid, timeout=5)
        elapsed = time.perf_counter() - t0
        print(f"  4 x 0.2s jobs on 4 workers took {elapsed:.2f}s "
              f"(sequential would be 0.8s)")

    # ---------------------------------------------------------------- P0
    section("2. Priority ordering")
    order = []
    order_lock = threading.Lock()

    def record(label):
        with order_lock:
            order.append(label)
        time.sleep(0.02)

    # ONE worker, so execution order is purely the queue's ordering.
    sched = Scheduler(n_workers=1, retry_policy=NoRetry())
    for label, priority in [("low-1", Priority.LOW),
                            ("low-2", Priority.LOW),
                            ("high-1", Priority.HIGH),
                            ("medium-1", Priority.MEDIUM),
                            ("high-2", Priority.HIGH)]:
        sched.submit(record, label, priority=priority, name=label)
    sched.start()
    time.sleep(0.6)
    sched.shutdown()

    print(f"  submitted: low-1, low-2, high-1, medium-1, high-2")
    print(f"  executed : {order}")
    print(f"  -> HIGH first, then MEDIUM, then LOW (FIFO within a level)")

    # ---------------------------------------------------------------- P1
    section("3. Retries with exponential backoff")
    with Scheduler(n_workers=2,
                   retry_policy=ExponentialBackoff(max_attempts=4, base=0.05)) as sched:
        flaky_id = sched.submit(flaky, name="flaky")
        result = sched.get_result(flaky_id, timeout=5)
        view = sched.get(flaky_id)
        print(f"  flaky task : {result}")
        print(f"  attempts   : {view.attempts}  status={view.status.value}")

        dead_id = sched.submit(always_fails, name="doomed")
        try:
            sched.get_result(dead_id, timeout=5)
        except RuntimeError as exc:
            print(f"  doomed task: gave up -> {exc}")
        print(f"  attempts   : {sched.get(dead_id).attempts} (max was 4)")

    # ---------------------------------------------------------------- P1
    section("4. Delayed execution")
    with Scheduler(n_workers=2, retry_policy=NoRetry()) as sched:
        t0 = time.perf_counter()
        delayed_id = sched.submit(add, 10, 5, run_after=0.4, name="delayed")
        immediate_id = sched.submit(add, 1, 1, name="immediate")

        sched.get_result(immediate_id, timeout=5)
        print(f"  immediate finished at {time.perf_counter() - t0:.2f}s")
        print(f"  delayed status now  : {sched.get_status(delayed_id).value}")

        value = sched.get_result(delayed_id, timeout=5)
        print(f"  delayed  finished at {time.perf_counter() - t0:.2f}s -> {value}")

    # ---------------------------------------------------------------- P1
    section("5. Cancellation")
    with Scheduler(n_workers=1, retry_policy=NoRetry()) as sched:
        blocker = sched.submit(slow_job, "blocker", 0.3, name="blocker")
        victim = sched.submit(add, 1, 1, name="victim", priority=Priority.LOW)

        time.sleep(0.05)
        sched.cancel(victim)
        print(f"  cancelled queued task -> {sched.get_status(victim).value}")

        time.sleep(0.4)
        print(f"  it never ran         -> result is {sched.get(victim).result}")

        try:
            sched.cancel(blocker)
        except TaskNotCancellableError as exc:
            print(f"  cancelling a finished task -> {type(exc).__name__}: {exc}")

    # ------------------------------------------------------------ thread safety
    section("6. Concurrent submission from many threads")
    with Scheduler(n_workers=8, queue_size=5000, retry_policy=NoRetry()) as sched:
        submitted = []
        sub_lock = threading.Lock()
        errors = []

        def submitter(worker_id):
            try:
                local = [sched.submit(add, worker_id, i) for i in range(50)]
                with sub_lock:
                    submitted.extend(local)
            except Exception as exc:            # noqa: BLE001
                errors.append(exc)

        threads = [threading.Thread(target=submitter, args=(i,)) for i in range(10)]
        t0 = time.perf_counter()
        for t in threads: t.start()
        for t in threads: t.join()

        for tid in submitted:
            sched.get_result(tid, timeout=20)
        elapsed = time.perf_counter() - t0

        print(f"  10 threads x 50 submits = {len(submitted)} tasks")
        print(f"  unique ids : {len(set(submitted))} (no id collisions)")
        print(f"  errors     : {len(errors)}")
        print(f"  completed  : {sched.stats()['SUCCEEDED']} in {elapsed:.2f}s")

    # ---------------------------------------------------------------- shutdown
    section("7. Graceful shutdown drains the queue")
    sched = Scheduler(n_workers=4, retry_policy=NoRetry()).start()
    for i in range(20):
        sched.submit(add, i, i)
    sched.shutdown(wait=True, timeout=5)

    stats = sched.stats()
    print(f"  submitted 20, then shutdown(wait=True)")
    print(f"  succeeded  : {stats['SUCCEEDED']}")
    print(f"  left queued: {stats['ready_queue']}")
    print(f"  stats      : {stats}")

    try:
        sched.submit(add, 1, 1)
    except Exception as exc:
        print(f"  submit after shutdown -> {type(exc).__name__}: {exc}")


if __name__ == "__main__":
    main()
