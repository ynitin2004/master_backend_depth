# Worked Example — Task Scheduler

A complete 90-minute machine coding round, with a running commentary on **what was written
when, and why**.

```bash
cd machine_coding/worked_example
python demo.py
python -m unittest test_scheduler.py -v      # 19 tests
```

> **The problem, as an interviewer would give it:**
> *"Design an in-memory task scheduler. Users submit tasks to be executed by a pool of
> worker threads. Support priorities. Failed tasks should be retried — make that
> configurable. Bonus: delayed execution and cancellation."*
>
> That's it. Deliberately vague. Everything below is what you do with it.

---

## The timeline

### 0:00–0:10 — clarify and scope

Asked four questions, wrote [`NOTES.md`](NOTES.md). **No code yet.**

The question that shaped everything: *"Are tasks submitted from multiple threads?"* — yes,
which made thread-safety a stated requirement rather than something I'd have to justify
later.

The word **"configurable"** in "configurable retries" is the interviewer handing you the
design hint. That's a `RetryPolicy` interface, and I said so out loud.

Then: *"I'll get submit-execute-query solid and tested first, then layer retries, delays and
cancellation. Sound right?"* — scope agreed, in writing, at minute 8.

### 0:10–0:20 — skeleton

In this order:

1. [`exceptions.py`](scheduler/exceptions.py) — 30 seconds, 4 classes
2. [`models.py`](scheduler/models.py) — `Task`, `TaskStatus`, `Priority`, `TaskView`
3. [`store.py`](scheduler/store.py) — the dict and the lock, created in the same minute
4. [`core.py`](scheduler/core.py) — public methods as stubs, signatures only
5. [`demo.py`](demo.py) — imported the stubs, printed a header, **ran it**

**At 0:19 `python demo.py` ran successfully** with zero real logic. From here every minute
made a working program better instead of hoping a broken one would come together.

### 0:20–0:55 — P0 core

Worker loop, ready queue, execution, status. The happy path worked at **0:51**.

### 0:55–1:10 — tests

Wrote the concurrency tests first, because those are the ones that catch real bugs. The
`test_task_executes_exactly_once` test is what proved the claim-transition was correct.

### 1:10–1:22 — P1

Retries, delayed execution, cancellation. Delayed execution was the risky one — a timer
thread is easy to get wrong — so it went **after** retries, which were trivial once the
policy interface existed.

### 1:22–1:30 — polish

Ran everything, deleted a dead variable, wrote this README. **Stopped coding at 1:22.**

---

## The architecture, in one picture

```
  submit(fn, priority, run_after)
            |
            +--- run_after > 0 ---> [ delayed heap ]      ordered by TIME
            |                        (min-heap + Condition)
            |                               |
            |                          timer thread
            |                          (sleeps until due)
            |                               |
            +--- run_after == 0 ------> [ ready PriorityQueue ]   ordered by PRIORITY
                                            (priority, seq, task_id)
                                                |
                                    +-----------+-----------+
                                 worker-0    worker-1    worker-N
                                    |           |           |
                                    +---> TaskStore (one RLock) <---+
```

**Two holding areas, because they answer different questions.** The heap answers *"what is
due next?"* (ordered by time). The queue answers *"what should run next?"* (ordered by
priority). Trying to serve both from one structure is where this design usually goes wrong.

---

## The five decisions worth defending

### 1. `TaskStore` owns all state and the only lock

Nothing else in the package touches `self._tasks`. One owner per piece of state means you
never have to reason about lock ordering — there's only one lock.

It's an `RLock` because `transition()` calls `_require()`, and a plain `Lock` would deadlock
against itself.

### 2. The guarded transition is the heart of the whole thing

```python
def transition(self, task_id, new_status, guard=None, mutate=None) -> bool:
    with self._lock:
        task = self._require(task_id)
        if guard is not None and not guard(task):
            return False
        task.status = new_status
        ...
```

Every state change is a **check-then-act**, and this method makes the check and the act
atomic. That single design choice is what gives you:

- **exactly-once execution** — a worker claims a task with
  `guard=lambda t: t.status is QUEUED`. If two workers ever dequeue the same id, only one
  wins the transition; the other returns immediately.
- **safe cancellation** — cancel and execute race on the same guard, so exactly one wins.
  Never both. `test_concurrent_cancel_and_execute` runs that race 20 times.

Say this out loud in the round: *"Every status change is a check-then-act, so they all go
through one guarded transition method rather than being scattered as `if status == X:
status = Y`."*

### 3. Callables run with no lock held

```python
fn, args, kwargs = self._read_callable(task_id)   # read under the lock
result = fn(*args, **kwargs)                      # run with NO lock held
```

The task is **arbitrary user code**. It can block, raise, sleep for an hour, or call back
into the scheduler. Running it under a lock would serialise every worker and invite
deadlock.

### 4. The timer thread sleeps on a `Condition`, not in a poll loop

Most candidates write `while True: check_due(); time.sleep(0.1)`. This instead waits exactly
until the next due time, and `submit()` notifies the condition so a sooner task wakes it
early. An idle scheduler burns zero CPU, and delays are precise rather than accurate to
±100 ms.

The promotion happens **outside** the delayed lock, because `queue.put()` can block on a
full queue — and blocking while holding a lock stalls every other thread.

### 5. The `seq` tiebreaker in the priority queue

```python
self._ready.put((int(priority), next(self._seq), task_id))
```

Without `seq`, two tasks of equal priority make the heap compare the *next* tuple element.
If that were a `Task` object you'd get `TypeError: '<' not supported between instances of
'Task'` — at runtime, under load, in front of the interviewer. It also makes ordering FIFO
within a priority level, which is what people expect.

This is a small detail that reliably impresses, because it only shows up in code written by
someone who has hit the bug.

---

## What was deliberately *not* built

Stating these is worth more than half-building them:

| Not built | How I'd add it |
|---|---|
| Persistence | `TaskStore` is already the seam — add a SQLite-backed implementation and inject it. |
| Cron scheduling | A `Trigger` abstraction alongside `run_after`; the timer loop already handles arbitrary future times. |
| Killing a running task | Impossible in Python. The task would take a `cancel_event` and check it — cooperative only. |
| Distributed workers | Replace the in-process `PriorityQueue` with a broker; the worker loop is unchanged. |
| Dead-letter queue | A second store for `FAILED` tasks; one extra branch in `_handle_failure`. |
| Per-task timeouts | Wrap execution in a `ThreadPoolExecutor` future with `result(timeout)` — but note that doesn't actually stop the work. |

---

## Follow-up questions you will be asked (and the answers)

**"What if two workers pull the same task?"**
They can't — each id is enqueued once. But even if they did, the guarded transition to
`RUNNING` means only one claims it and the other returns. That's tested.

**"How do you stop a running task?"**
You can't kill a thread in Python. `cancel()` only works on tasks that haven't started; a
running task would have to accept a cancel `Event` and check it. I'd surface that in the
task signature rather than pretend otherwise.

**"What if the queue fills up?"**
`submit()` blocks — that's intentional backpressure. I'd add a `timeout` parameter so
callers can fail fast instead. An unbounded queue would just move the failure to an OOM.

**"How would you add task dependencies (run B after A)?"**
A dependency map in the store plus a `WAITING` status. On a task's success, check its
dependents and promote any whose dependencies are all satisfied. The transition method
already gives me the atomicity for that check.

**"Is this CPU-bound safe?"**
No — the GIL means CPU-bound tasks won't parallelise. For those I'd swap the worker threads
for a `ProcessPoolExecutor`, which requires tasks to be picklable. The interface wouldn't
change.

**"Why poll in `get_result` instead of using an Event?"**
A per-task `Event` would be cleaner and wake instantly, at the cost of one Event object per
task. With millions of tasks that matters; here it doesn't. Deliberate trade-off, easy to
change.

---

## Score this against the rubric

Run [`../RUBRIC.md`](../RUBRIC.md) over this code as practice at *reading* for the criteria:

- **Section A (works):** 40/40 — demo runs, 19 tests pass, all P0+P1 features demonstrated
- **Section B (concurrency):** 25/25 — one lock owner, guarded transitions, cooperative
  shutdown joined with timeouts, workers wrapped in `try/except`, no lock held across user code
- **Section C (design):** 20/20 — models/store/service split, `RetryPolicy` ABC with three
  implementations, injected dependencies, custom exceptions
- **Section D (tests):** 10/10 — 19 tests, four genuinely concurrent, all invariant-based
- **Section E (communication):** 5/5 — NOTES.md tiers, README, "not done" section

---

## Your turn

1. **Read** every file in [`scheduler/`](scheduler/) top to bottom. Understand *why* each
   lock is where it is.
2. **Re-type it from scratch**, looking only at [`NOTES.md`](NOTES.md). Not copy-paste —
   type it. Time yourself.
3. **Do it again a week later.** It should take you under 60 minutes.
4. Then go to [`../problems/`](../problems/) and do one cold, on the clock.

The second re-type is where it clicks. The structure stops being something you remember and
becomes something you reach for.
