"""Written 0:20-0:55 (P0) then 0:55-1:20 (P1). The orchestration layer.

ARCHITECTURE
    submit() ---> [delayed heap] --timer thread--> [ready PriorityQueue] --> workers
                   (run_at > now)                   (priority, seq, id)

    Two holding areas because they answer different questions:
      - the heap is ordered by TIME     ("what is due next?")
      - the queue is ordered by PRIORITY ("what should run next?")
"""

import heapq
import itertools
import threading
import time
from queue import Empty, PriorityQueue
from typing import Any, Callable, Optional

from .exceptions import (
    SchedulerShutdownError,
    TaskNotCancellableError,
    TaskNotFoundError,
)
from .models import Priority, Task, TaskStatus, TaskView
from .retry import ExponentialBackoff, RetryPolicy
from .store import TaskStore


class Scheduler:
    def __init__(self, n_workers: int = 4, queue_size: int = 1000,
                 retry_policy: Optional[RetryPolicy] = None,
                 store: Optional[TaskStore] = None):
        # Injected, not hardcoded -- lets you say "I'd swap in a persistent
        # store here" without writing it.
        self._store = store or TaskStore()
        self._retry_policy = retry_policy or ExponentialBackoff()

        # maxsize -> backpressure. An unbounded queue lets a fast producer
        # eat all your memory.
        self._ready: PriorityQueue = PriorityQueue(maxsize=queue_size)

        # Delayed tasks: a heap of (run_at, task_id), guarded by a Condition
        # so the timer thread sleeps exactly until the next due time instead
        # of polling.
        self._delayed: list[tuple[float, str]] = []
        self._delayed_cond = threading.Condition()

        self._ids = itertools.count(1)
        self._seq = itertools.count()          # PriorityQueue tiebreaker
        self._id_lock = threading.Lock()

        self._stop = threading.Event()
        self._started = False
        self._lifecycle_lock = threading.Lock()

        self._workers = [
            threading.Thread(target=self._worker_loop, name=f"worker-{i}",
                             daemon=True)
            for i in range(n_workers)
        ]
        self._timer = threading.Thread(target=self._timer_loop, name="timer",
                                       daemon=True)

    # ====================================================== public API (P0)
    def start(self) -> "Scheduler":
        with self._lifecycle_lock:
            if self._started:
                return self
            self._started = True
        for worker in self._workers:
            worker.start()
        self._timer.start()
        return self

    def submit(self, fn: Callable[..., Any], *args,
               name: Optional[str] = None,
               priority: Priority = Priority.MEDIUM,
               run_after: float = 0.0,
               **kwargs) -> str:
        """Accept a task. Returns its id immediately -- never blocks on execution."""
        if self._stop.is_set():
            raise SchedulerShutdownError("scheduler is shutting down")
        if not callable(fn):
            raise TypeError("fn must be callable")
        if run_after < 0:
            raise ValueError("run_after must be >= 0")

        task = Task(
            id=self._next_id(),
            name=name or getattr(fn, "__name__", "task"),
            fn=fn, args=args, kwargs=kwargs,
            priority=priority,
            run_at=time.monotonic() + run_after,
        )
        self._store.add(task)

        if run_after > 0:
            self._schedule_delayed(task)
        else:
            self._enqueue_ready(task.id, task.priority)
            self._store.transition(task.id, TaskStatus.QUEUED)
        return task.id

    def get(self, task_id: str) -> TaskView:
        return self._store.get(task_id)

    def get_status(self, task_id: str) -> TaskStatus:
        return self._store.get(task_id).status

    def get_result(self, task_id: str, timeout: Optional[float] = None) -> Any:
        """Block until the task reaches a terminal state, then return or raise.

        Polling with a small sleep, deliberately: a per-task Event would be
        cleaner but costs memory per task. Worth SAYING that trade-off out
        loud rather than leaving it to be discovered.
        """
        deadline = None if timeout is None else time.monotonic() + timeout
        while True:
            view = self._store.get(task_id)
            if view.status.is_terminal:
                if view.status is TaskStatus.FAILED:
                    raise RuntimeError(f"task {task_id} failed: {view.error}")
                return view.result
            if deadline is not None and time.monotonic() >= deadline:
                raise TimeoutError(f"task {task_id} still {view.status}")
            time.sleep(0.005)

    # ====================================================== public API (P1)
    def cancel(self, task_id: str) -> bool:
        """Cancel a task that hasn't started. Returns True if cancelled.

        A RUNNING task cannot be cancelled -- there is no way to kill a thread
        in Python. Real cancellation would need the task itself to check an
        Event, which I'd mention as the extension.
        """
        if task_id not in self._store:
            raise TaskNotFoundError(task_id)

        cancelled = self._store.transition(
            task_id, TaskStatus.CANCELLED,
            guard=lambda t: t.status in (TaskStatus.PENDING, TaskStatus.QUEUED),
        )
        if not cancelled:
            raise TaskNotCancellableError(task_id, self._store.get(task_id).status)
        # The id stays in the ready queue as a tombstone; the worker sees the
        # CANCELLED status and skips it. Cheaper than removing from a heap.
        return True

    def shutdown(self, wait: bool = True, timeout: float = 5.0) -> None:
        """Cooperative shutdown. Idempotent."""
        self._stop.set()
        with self._delayed_cond:
            self._delayed_cond.notify_all()    # wake the timer out of its wait

        if wait:
            # Drain the backlog before telling workers to exit.
            deadline = time.monotonic() + timeout
            while not self._ready.empty() and time.monotonic() < deadline:
                time.sleep(0.01)

        for thread in (*self._workers, self._timer):
            if thread.is_alive():
                thread.join(timeout=timeout)   # ALWAYS with a timeout

    def stats(self) -> dict[str, Any]:
        counts = self._store.count_by_status()
        counts["total"] = len(self._store)
        counts["ready_queue"] = self._ready.qsize()
        with self._delayed_cond:
            counts["delayed"] = len(self._delayed)
        return counts

    def __enter__(self):
        return self.start()

    def __exit__(self, *exc):
        self.shutdown()

    # ========================================================== worker loop
    def _worker_loop(self) -> None:
        while True:
            try:
                # Short timeout so we re-check the stop flag rather than
                # blocking on get() forever.
                _priority, _seq, task_id = self._ready.get(timeout=0.1)
            except Empty:
                if self._stop.is_set():
                    return
                continue

            try:
                self._execute(task_id)
            except Exception:
                # A worker that lets an exception escape DIES and the pool
                # silently shrinks. Never let that happen.
                pass
            finally:
                self._ready.task_done()

    def _execute(self, task_id: str) -> None:
        # Claim the task. The guard makes this atomic: if two workers somehow
        # both dequeue this id, only one wins the transition to RUNNING.
        # A CANCELLED task fails the guard and is skipped here.
        claimed = self._store.transition(
            task_id, TaskStatus.RUNNING,
            guard=lambda t: t.status is TaskStatus.QUEUED,
            mutate=lambda t: setattr(t, "started_at", time.monotonic()),
        )
        if not claimed:
            return

        # Read what we need, then run the callable with NO LOCK HELD.
        # Running arbitrary user code while holding a lock is how you deadlock.
        fn, args, kwargs = self._read_callable(task_id)

        try:
            result = fn(*args, **kwargs)
        except Exception as exc:
            self._handle_failure(task_id, exc)
        else:
            self._store.transition(
                task_id, TaskStatus.SUCCEEDED,
                mutate=lambda t: (setattr(t, "result", result),
                                  setattr(t, "attempts", t.attempts + 1),
                                  setattr(t, "finished_at", time.monotonic())),
            )

    def _handle_failure(self, task_id: str, exc: Exception) -> None:
        attempts = self._bump_attempts(task_id)

        if self._retry_policy.should_retry(attempts, exc):
            delay = self._retry_policy.delay_for(attempts)
            self._store.transition(
                task_id, TaskStatus.PENDING,
                mutate=lambda t: (setattr(t, "error", f"{type(exc).__name__}: {exc}"),
                                  setattr(t, "run_at", time.monotonic() + delay)),
            )
            self._schedule_delayed_by_id(task_id, time.monotonic() + delay)
            return

        self._store.transition(
            task_id, TaskStatus.FAILED,
            mutate=lambda t: (setattr(t, "error", f"{type(exc).__name__}: {exc}"),
                              setattr(t, "finished_at", time.monotonic())),
        )

    # =========================================================== timer loop
    def _timer_loop(self) -> None:
        """Promotes delayed tasks into the ready queue when they come due.

        Sleeps on a Condition until the next due time instead of polling, so
        an idle scheduler burns no CPU. This is the piece most candidates
        implement as `while True: sleep(0.1)`.
        """
        while not self._stop.is_set():
            with self._delayed_cond:
                if not self._delayed:
                    self._delayed_cond.wait(timeout=0.1)
                    continue

                run_at, task_id = self._delayed[0]
                now = time.monotonic()
                if run_at > now:
                    # Wait exactly until it's due -- or until submit() adds
                    # something sooner and notifies us.
                    self._delayed_cond.wait(timeout=run_at - now)
                    continue

                heapq.heappop(self._delayed)

            # Promote OUTSIDE the delayed lock: enqueueing can block on a
            # full ready queue, and blocking while holding a lock is how you
            # stall every other thread.
            view = self._store.get(task_id)
            if view.status.is_terminal:
                continue                       # cancelled while it waited
            self._enqueue_ready(task_id, view.priority)
            self._store.transition(
                task_id, TaskStatus.QUEUED,
                guard=lambda t: t.status is TaskStatus.PENDING,
            )

    # ============================================================== helpers
    def _enqueue_ready(self, task_id: str, priority: Priority) -> None:
        # The seq tiebreaker is essential: without it, two tasks of equal
        # priority make the heap compare the next tuple element, and if that
        # were a Task object you'd get "TypeError: '<' not supported".
        # It also makes ordering FIFO within a priority level.
        self._ready.put((int(priority), next(self._seq), task_id))

    def _schedule_delayed(self, task: Task) -> None:
        self._schedule_delayed_by_id(task.id, task.run_at)

    def _schedule_delayed_by_id(self, task_id: str, run_at: float) -> None:
        with self._delayed_cond:
            heapq.heappush(self._delayed, (run_at, task_id))
            # Notify so the timer re-evaluates: this task may be due sooner
            # than whatever it is currently waiting for.
            self._delayed_cond.notify_all()

    def _read_callable(self, task_id: str):
        holder = {}
        self._store.update(task_id, lambda t: holder.update(
            fn=t.fn, args=t.args, kwargs=t.kwargs))
        return holder["fn"], holder["args"], holder["kwargs"]

    def _bump_attempts(self, task_id: str) -> int:
        holder = {}

        def mutate(task):
            task.attempts += 1
            holder["attempts"] = task.attempts

        self._store.update(task_id, mutate)
        return holder["attempts"]

    def _next_id(self) -> str:
        with self._id_lock:
            return f"task-{next(self._ids)}"
