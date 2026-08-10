# Task Scheduler — scope

*Written at minute 3, before any code. This exact file, typed in the round.*

## Clarifying questions asked

- Q: In-memory, single process?
  A: Yes, no persistence needed.
- Q: Are tasks submitted from multiple threads?
  A: Yes, assume a web server calling in from many request threads.
- Q: Do you want breadth of features or depth on the core?
  A: Depth. Get execution solid.
- Q: Should failed tasks retry?
  A: Yes, that's important. Configurable.

## P0 — must work (target 0:55)

- [x] `submit(fn, *args, priority=...)` returns a task id
- [x] a fixed worker pool executes tasks concurrently
- [x] higher-priority tasks run first
- [x] `get_status(task_id)` / `get_result(task_id)`

## P1 — if time (target 1:20)

- [x] retries with configurable backoff policy
- [x] delayed execution (`run_after=5.0`)
- [x] cancellation of a task that hasn't started
- [x] graceful shutdown that drains the queue

## P2 — mention, don't build

- persistence (store is already an interface — drop in SQLite)
- cron expressions (add a `Trigger` abstraction next to `run_after`)
- distributed workers (replace the in-process queue with a broker)
- metrics export, dead-letter queue for permanently-failed tasks

## Assumptions

- in-memory, single process
- thread-safe: `submit` is called from many threads
- tasks are Python callables; args must not be mutated by the caller after submit
- I/O-bound tasks → threads are the right tool (CPU-bound would need processes)

## Design decisions

- `TaskStore` owns all task state behind one RLock. Nothing else locks task state.
- Ready tasks live in a `PriorityQueue` of `(priority, seq, task_id)`.
  The seq tiebreaker stops the heap comparing `Task` objects.
- Delayed tasks live in a heap behind a `Condition`; one timer thread promotes them.
- `RetryPolicy` is an ABC — the problem said "configurable", which is the hint to
  use an interface. Two implementations, `NoRetry` and `ExponentialBackoff`.
- Shutdown is cooperative (`Event`), never `daemon`-and-hope.
