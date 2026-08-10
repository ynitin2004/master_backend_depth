"""Written at 0:55-1:10. The five categories, in order.

Run:  python -m unittest test_scheduler.py -v
"""

import threading
import time
import unittest

from scheduler import (
    ExponentialBackoff,
    FixedDelay,
    NoRetry,
    Priority,
    Scheduler,
    TaskStatus,
)
from scheduler.exceptions import (
    SchedulerShutdownError,
    TaskNotCancellableError,
    TaskNotFoundError,
)


def add(a, b):
    return a + b


def boom():
    raise ConnectionError("nope")


class TestScheduler(unittest.TestCase):

    def setUp(self):
        self.sched = Scheduler(n_workers=4, retry_policy=NoRetry()).start()

    def tearDown(self):
        self.sched.shutdown(wait=False, timeout=2)

    # ------------------------------------------------------------- 1. happy
    def test_submit_and_get_result(self):
        task_id = self.sched.submit(add, 2, 3)
        self.assertEqual(self.sched.get_result(task_id, timeout=5), 5)
        self.assertEqual(self.sched.get_status(task_id), TaskStatus.SUCCEEDED)
        self.assertEqual(self.sched.get(task_id).attempts, 1)

    def test_many_tasks_all_complete(self):
        ids = [self.sched.submit(add, i, i) for i in range(50)]
        results = [self.sched.get_result(tid, timeout=20) for tid in ids]
        self.assertEqual(results, [i * 2 for i in range(50)])

    def test_priority_ordering(self):
        order = []
        lock = threading.Lock()

        def record(label):
            with lock:
                order.append(label)

        # One worker so ordering is purely the queue's doing.
        sched = Scheduler(n_workers=1, retry_policy=NoRetry())
        for label, priority in [("l1", Priority.LOW), ("h1", Priority.HIGH),
                                ("m1", Priority.MEDIUM), ("h2", Priority.HIGH)]:
            sched.submit(record, label, priority=priority)
        sched.start()
        time.sleep(0.5)
        sched.shutdown()

        self.assertEqual(order, ["h1", "h2", "m1", "l1"])

    # --------------------------------------------------------------- 2. edge
    def test_delayed_execution(self):
        task_id = self.sched.submit(add, 1, 1, run_after=0.3)
        self.assertIn(self.sched.get_status(task_id),
                      (TaskStatus.PENDING, TaskStatus.QUEUED))
        time.sleep(0.1)
        self.assertNotEqual(self.sched.get_status(task_id), TaskStatus.SUCCEEDED)

        self.assertEqual(self.sched.get_result(task_id, timeout=5), 2)

    def test_cancel_before_start(self):
        # Occupy the single worker so the victim can't start.
        sched = Scheduler(n_workers=1, retry_policy=NoRetry()).start()
        sched.submit(time.sleep, 0.4)
        victim = sched.submit(add, 1, 1, priority=Priority.LOW)

        time.sleep(0.05)
        self.assertTrue(sched.cancel(victim))
        self.assertEqual(sched.get_status(victim), TaskStatus.CANCELLED)

        time.sleep(0.5)
        self.assertIsNone(sched.get(victim).result, "cancelled task still ran")
        sched.shutdown()

    def test_stats(self):
        for i in range(5):
            self.sched.submit(add, i, i)
        time.sleep(0.3)
        stats = self.sched.stats()
        self.assertEqual(stats["total"], 5)
        self.assertEqual(stats["SUCCEEDED"], 5)

    # -------------------------------------------------------------- 3. error
    def test_error_paths(self):
        with self.assertRaises(TaskNotFoundError):
            self.sched.get("no-such-task")

        with self.assertRaises(TypeError):
            self.sched.submit("not callable")

        with self.assertRaises(ValueError):
            self.sched.submit(add, 1, 1, run_after=-1)

        failing = self.sched.submit(boom)
        with self.assertRaises(RuntimeError):
            self.sched.get_result(failing, timeout=5)
        self.assertEqual(self.sched.get_status(failing), TaskStatus.FAILED)
        self.assertIn("ConnectionError", self.sched.get(failing).error)

    def test_cannot_cancel_finished_task(self):
        task_id = self.sched.submit(add, 1, 1)
        self.sched.get_result(task_id, timeout=5)
        with self.assertRaises(TaskNotCancellableError):
            self.sched.cancel(task_id)

    def test_submit_after_shutdown_rejected(self):
        sched = Scheduler(n_workers=2).start()
        sched.shutdown()
        with self.assertRaises(SchedulerShutdownError):
            sched.submit(add, 1, 1)

    def test_get_result_timeout(self):
        task_id = self.sched.submit(time.sleep, 2)
        with self.assertRaises(TimeoutError):
            self.sched.get_result(task_id, timeout=0.1)

    # ------------------------------------------------------------ 4. retries
    def test_retry_eventually_succeeds(self):
        attempts = {"n": 0}
        lock = threading.Lock()

        def flaky():
            with lock:
                attempts["n"] += 1
                n = attempts["n"]
            if n < 3:
                raise ConnectionError("transient")
            return "ok"

        sched = Scheduler(n_workers=2,
                          retry_policy=FixedDelay(max_attempts=5, delay=0.02)).start()
        task_id = sched.submit(flaky)
        self.assertEqual(sched.get_result(task_id, timeout=10), "ok")
        self.assertEqual(sched.get(task_id).attempts, 3)
        sched.shutdown()

    def test_retry_gives_up(self):
        sched = Scheduler(n_workers=2,
                          retry_policy=FixedDelay(max_attempts=3, delay=0.01)).start()
        task_id = sched.submit(boom)
        with self.assertRaises(RuntimeError):
            sched.get_result(task_id, timeout=10)
        self.assertEqual(sched.get(task_id).attempts, 3)
        self.assertEqual(sched.get_status(task_id), TaskStatus.FAILED)
        sched.shutdown()

    def test_retry_policy_respects_exception_type(self):
        # ExponentialBackoff only retries `retry_on` types.
        policy = ExponentialBackoff(max_attempts=5, base=0.01,
                                    retry_on=(ConnectionError,))
        sched = Scheduler(n_workers=2, retry_policy=policy).start()

        def bad_value():
            raise ValueError("permanent")

        task_id = sched.submit(bad_value)
        with self.assertRaises(RuntimeError):
            sched.get_result(task_id, timeout=5)
        self.assertEqual(sched.get(task_id).attempts, 1, "should not have retried")
        sched.shutdown()

    # -------------------------------------------------- 5. THE CONCURRENCY ONE
    def test_concurrent_submissions(self):
        errors = []
        submitted = []
        lock = threading.Lock()
        n_threads, per_thread = 10, 50

        def submitter(worker_id):
            try:
                local = [self.sched.submit(add, worker_id, i)
                         for i in range(per_thread)]
                with lock:
                    submitted.extend(local)
            except Exception as exc:            # noqa: BLE001
                errors.append(exc)

        threads = [threading.Thread(target=submitter, args=(i,))
                   for i in range(n_threads)]
        for t in threads: t.start()
        for t in threads: t.join(timeout=20)

        self.assertFalse(errors, f"errors under concurrency: {errors[:3]}")
        expected = n_threads * per_thread
        self.assertEqual(len(submitted), expected)
        self.assertEqual(len(set(submitted)), expected, "id generator raced")

        for task_id in submitted:
            self.sched.get_result(task_id, timeout=30)
        self.assertEqual(self.sched.stats()["SUCCEEDED"], expected)

    def test_task_executes_exactly_once(self):
        """The invariant that a broken claim-transition would violate."""
        runs = []
        lock = threading.Lock()

        def record():
            with lock:
                runs.append(1)

        sched = Scheduler(n_workers=16, retry_policy=NoRetry()).start()
        ids = [sched.submit(record) for _ in range(200)]
        for task_id in ids:
            sched.get_result(task_id, timeout=30)
        sched.shutdown()

        self.assertEqual(len(runs), 200, "a task ran more or less than once")

    def test_concurrent_cancel_and_execute(self):
        """Exactly one of {cancelled, executed} must win -- never both."""
        for _ in range(20):
            sched = Scheduler(n_workers=2, retry_policy=NoRetry()).start()
            ran = []
            lock = threading.Lock()

            def work():
                with lock:
                    ran.append(1)

            task_id = sched.submit(work)
            cancelled = []

            def try_cancel():
                try:
                    cancelled.append(sched.cancel(task_id))
                except TaskNotCancellableError:
                    cancelled.append(False)

            t = threading.Thread(target=try_cancel)
            t.start()
            t.join(timeout=5)
            time.sleep(0.1)

            status = sched.get_status(task_id)
            if status is TaskStatus.CANCELLED:
                self.assertEqual(len(ran), 0, "cancelled task still executed")
            else:
                self.assertEqual(len(ran), 1)
            sched.shutdown(wait=False)

    # ----------------------------------------------------------- 6. shutdown
    def test_shutdown_drains_queue(self):
        sched = Scheduler(n_workers=4, retry_policy=NoRetry()).start()
        for i in range(30):
            sched.submit(add, i, i)
        sched.shutdown(wait=True, timeout=10)

        stats = sched.stats()
        self.assertEqual(stats["SUCCEEDED"], 30, f"work was dropped: {stats}")

    def test_shutdown_is_idempotent(self):
        sched = Scheduler(n_workers=2).start()
        sched.shutdown(timeout=2)
        sched.shutdown(timeout=2)          # must not raise

    def test_context_manager(self):
        with Scheduler(n_workers=2, retry_policy=NoRetry()) as sched:
            task_id = sched.submit(add, 40, 2)
            self.assertEqual(sched.get_result(task_id, timeout=5), 42)


if __name__ == "__main__":
    unittest.main(verbosity=2)
