# Multithreading Interview Q&A

Answer these **out loud** before reading the answer. Being able to recognise a correct
answer is not the same as being able to produce one under pressure.

Ordered roughly by how often they come up.

---

## Tier 1 — You will be asked these

### 1. What's the difference between a process and a thread?

A process is a running program with its own memory space. A thread is a unit of execution
inside a process; all threads of a process **share its memory** (heap, globals, file
handles) but each has its own **call stack and local variables**.

Consequences: threads communicate cheaply (just touch a shared variable) but need
synchronization to avoid corrupting it. Processes are isolated — safe by default, but
communication requires serialization (pickling) through pipes, queues, or shared memory.

---

### 2. What is the GIL and why does it exist?

The **Global Interpreter Lock** is a mutex in CPython that allows only one thread to execute
Python bytecode at a time.

**Why it exists:** CPython's memory management uses non-atomic reference counting. Without
the GIL every `Py_INCREF`/`Py_DECREF` would need its own lock, which would be slow and
deadlock-prone. The GIL makes single-threaded code fast and C extensions easy to write.

**Consequence:** Python threads give you **no CPU parallelism**. Four threads doing math on
four cores run no faster than one.

**But** the GIL is released during I/O (sockets, files, `time.sleep`), while waiting on
locks, and inside many C extensions (NumPy, zlib, hashlib). That's where threading wins.

**Bonus point to score:** the GIL is a *CPython implementation detail*, not part of the
language. Jython and IronPython have none, and CPython 3.13 introduced an experimental
free-threaded build (PEP 703) that removes it.

---

### 3. When would you use threads vs processes vs asyncio?

| Workload | Choice | Why |
|---|---|---|
| I/O-bound with blocking libraries | **threads** | GIL released while waiting |
| CPU-bound | **processes** | each has its own interpreter & GIL |
| I/O-bound, thousands of connections, async libs | **asyncio** | ~KBs per task instead of MBs |

"If unsure, I'd start with `ThreadPoolExecutor` and measure — I wouldn't reach for
multiprocessing without evidence the work is actually CPU-bound."

---

### 4. What's a race condition? Give an example.

When the result depends on the unpredictable timing of threads. Classic:

```python
counter += 1        # LOAD, ADD, STORE — three separate steps
```

Two threads can both LOAD 41, both compute 42, both STORE 42. One increment is lost.

The more dangerous form in real code is **check-then-act**:

```python
if key not in cache:          # thread A and thread B both pass this
    cache[key] = expensive()  # both run expensive(); you leak a connection
```

**Fix:** put the check and the act inside one lock acquisition.

---

### 5. Difference between `Lock` and `RLock`?

`Lock` is not reentrant — a thread that already holds it and tries to acquire it again
deadlocks against itself. `RLock` can be acquired multiple times **by the same thread** and
must be released the same number of times.

Use `RLock` for recursive functions and for classes where one locked method calls another
locked method. Use `Lock` otherwise — it's cheaper and its stricter behaviour surfaces
accidental nesting.

---

### 6. What happens if you call `t.run()` instead of `t.start()`?

`run()` executes the target **on the current thread** — no new thread is created at all.
`start()` spawns the OS thread, which then calls `run()`.

Related traps: `start()` twice raises `RuntimeError` (a `Thread` object is single-use), and
`join()` always returns `None` — check `is_alive()` to find out whether a `join(timeout)`
actually completed.

---

### 7. How do you get a return value out of a thread?

`Thread(target=fn)` discards `fn`'s return value. Options:

1. Subclass `Thread` and store `self.result`; read it after `join()`.
2. Push to a `queue.Queue`.
3. **`ThreadPoolExecutor` + `future.result()`** — the right answer in production.

Same for exceptions: an exception in a raw thread prints a traceback and vanishes; it never
reaches the caller. `future.result()` re-raises it in the calling thread, which is the main
reason to prefer the pool.

---

### 8. What's a daemon thread?

A thread the interpreter will **not wait for** at exit — it's killed abruptly, with no
cleanup and no `finally` blocks. Set `daemon=True` *before* `start()`.

Use for background chores where abrupt death is harmless (heartbeat, metrics). **Never** for
anything holding a file handle, a lock, or unflushed data.

---

### 9. How do you stop a thread?

**You can't** — Python has no `thread.kill()`, by design (killing a thread holding a lock
would deadlock the process). The only correct answer is **cooperative cancellation**:

```python
stop = threading.Event()

def worker():
    while not stop.is_set():
        do_a_chunk()
        stop.wait(5)      # NOT time.sleep(5) — this wakes instantly on set()

stop.set()
t.join(timeout=10)
```

The `stop.wait()` detail is the part that separates a good answer from a great one: with
`time.sleep(5)` your shutdown takes up to 5 seconds; with `stop.wait(5)` it's immediate.

---

## Tier 2 — Common follow-ups

### 10. Is `list.append()` thread-safe?

Effectively yes under the GIL — it's a single bytecode, so no items are lost.
**But don't rely on it.** It's a CPython implementation detail, it doesn't hold on
free-threaded builds, and — most importantly — it doesn't help you the moment you need
*two* operations to be atomic together:

```python
if x not in lst:     # <-- the gap between these two lines is the bug
    lst.append(x)
```

The professional answer: "it happens to be, but I'd still use a lock, because the guarantee
I actually need is about my *invariant*, not about one method call."

---

### 11. What is a deadlock and how do you prevent it?

Two or more threads each holding a lock the other needs — nobody can proceed. Requires all
four **Coffman conditions**: mutual exclusion, hold-and-wait, no preemption, circular wait.
Break any one and deadlock is impossible.

**Prevention, in order of preference:**
1. **Global lock ordering** — always acquire locks in the same order (e.g. sorted by
   account id). Breaks circular wait. This is the standard fix.
2. `acquire(timeout=...)`, release everything, back off with jitter, retry. Breaks
   hold-and-wait. Costs retries and can livelock without the jitter.
3. Hold one lock at a time, or use one coarser lock.

Also: never call unknown/callback code while holding a lock — you don't know what *it*
locks.

**Diagnosis:** the process sits at 0% CPU with no output. Use
`faulthandler.dump_traceback_later(30)` or `py-spy dump --pid`; any thread parked in
`lock.acquire()` is a suspect.

---

### 12. Why must `Condition.wait()` be in a `while` loop, not an `if`?

Two reasons:

1. **The state can change between the notify and your wake-up.** `notify_all()` wakes
   everyone, but only one thread gets the lock first — it may consume the item, so the
   others wake to find the condition false again.
2. **Spurious wakeups are explicitly permitted** — `wait()` may return without any notify.

`while` re-checks and goes back to sleep. There is no correct use of `if` here.
`cond.wait_for(predicate)` is the tidy shorthand.

---

### 13. `notify()` vs `notify_all()`?

`notify()` wakes one waiter; `notify_all()` wakes all. `notify()` is cheaper but incorrect
whenever waiters are waiting for *different* conditions — you might wake a thread that can't
proceed, it goes back to sleep, and the one that could proceed is never woken. **Default to
`notify_all()`** unless you've proven all waiters are interchangeable.

---

### 14. `Semaphore` vs `Lock` vs `BoundedSemaphore`?

- `Lock` — one holder. Has an owner concept.
- `Semaphore(n)` — up to n holders. Just a counter; any thread can `release()` one it never
  acquired, and over-releasing silently *raises* the ceiling.
- `BoundedSemaphore(n)` — same, but over-releasing raises `ValueError`. Use this when the
  count represents a real resource limit, so the bug is caught instead of silently doubling
  your connection pool.

---

### 15. What does `queue.Queue` give you over a list + lock?

It's already thread-safe (locks and conditions inside), plus:
- **blocking** `get()`/`put()` — no busy-waiting
- **`maxsize`** — backpressure, so a fast producer can't exhaust memory
- **`task_done()`/`join()`** — wait until all work is *finished*, not just dequeued
- `LifoQueue`, `PriorityQueue` variants

Traps: `empty()`/`qsize()` are immediately stale — never write `if not q.empty(): q.get()`;
use `get_nowait()` with `except queue.Empty`. And every `get()` needs a matching
`task_done()` (in a `finally`), or `q.join()` hangs forever.

---

### 16. How do you shut down a pool of queue consumers?

**Sentinel values** — push one per consumer:

```python
SENTINEL = object()
for _ in range(n_workers):
    q.put(SENTINEL)
```

Each worker sees exactly one, breaks, exits. Order matters: `q.join()` to drain the backlog
**first**, then signal shutdown — reversing it drops queued work.

In a multi-stage pipeline, sentinels must **cascade**: stage 2 can only send stage 3's
sentinels once *every* stage-2 worker has finished, not when the first one does.

---

### 17. How do you size a thread pool?

- **CPU-bound:** a thread pool is the wrong tool. Use `ProcessPoolExecutor(max_workers=cpu_count())`.
- **I/O-bound:** far more than core count is fine. Tune against the *remote* service's
  limits, connection pool size, and memory (~8 MB of stack per thread) — not your CPU.
  32–64 is a normal starting point.
- Default is `min(32, os.cpu_count() + 4)`.

"I'd start with a default, measure p99 latency and throughput, and raise it until the
downstream service becomes the bottleneck."

---

### 18. What's the difference between `pool.map` and `submit` + `as_completed`?

`map` returns results in **input order** and raises on the first exception when you iterate
— you lose the later results even if they succeeded. `submit` + `as_completed` yields in
**completion order**, lets you handle each failure individually, and lets you show progress.

Use `map` for simple all-or-nothing work; `submit`/`as_completed` when partial failure is
normal (which, for network work, it is).

---

### 19. `future.result(timeout=5)` timed out. Is the task cancelled?

**No.** It's still running and still occupying a worker. `result(timeout)` bounds *your
wait*, not the task. `future.cancel()` only works if the task hasn't started yet.

Real cancellation must be cooperative: the task checks an `Event`, or the underlying call
takes its own timeout (`requests.get(url, timeout=5)`).

---

### 20. What is `threading.local()` for?

An object whose attributes are per-thread — same variable name, different value in each
thread. Used for per-thread DB connections, HTTP sessions, and request IDs, so you don't
have to thread context through every function signature.

**The trap:** thread pools *reuse* threads, so a thread-local set by task 1 is still there
for task 5. Always initialise it at the start of each task (or use the pool's
`initializer=`).

---

## Tier 3 — Senior / design questions

### 21. Implement a thread-safe bounded blocking queue.

See [exercises/solutions/sol05_bounded_queue.py](exercises/solutions/sol05_bounded_queue.py).
Key points to say while writing it: one lock with two `Condition`s (`not_full`,
`not_empty`); `while` loops around `wait()`; a deadline computed **once** for timeouts, not
a fresh `timeout` per loop iteration.

---

### 22. Implement a read-write lock. How do you avoid writer starvation?

See [exercises/solutions/sol13_rwlock.py](exercises/solutions/sol13_rwlock.py). The key
insight: keep a **`waiting_writers` counter**, incremented *before* the writer waits, and
make new readers block while it's non-zero. Without it, a continuous stream of readers keeps
the reader count above zero forever and the writer never runs.

Name the trade-off: reader-preferring (max read throughput, writers can starve),
writer-preferring (bounded writer latency), fair/FIFO (no starvation, lowest throughput).

Also mention: Python has no RWLock in the stdlib, it's not reentrant, and for short critical
sections a plain `Lock` beats it because the bookkeeping costs more than it saves.

---

### 23. How do you prevent a cache stampede?

When a hot key expires, 10,000 concurrent requests all miss and all hit the database.

**Single-flight** with a **per-key lock**: the first thread computes, the rest wait on that
key's lock and get the cached value after double-checking. Crucially the compute happens
**without** holding the global guard lock, so different keys don't block each other.

See [exercises/solutions/sol12_single_flight.py](exercises/solutions/sol12_single_flight.py).
Bonus: mention that the per-key lock dict grows forever unless you clean up, and that
**lock striping** (`hash(key) % 64` locks) bounds the memory.

---

### 24. Dining philosophers — how do you solve it?

Five philosophers, five forks, each needs both neighbours' forks. Naive "left then right"
deadlocks when everyone grabs left simultaneously.

Map each fix to a Coffman condition:
- **Resource ordering** (always take the lower-numbered fork first) → breaks circular wait
- **Semaphore(n-1)** (only four seated) → breaks hold-and-wait
- **Asymmetry** (odd philosophers take right first) → breaks circular wait

You can't break mutual exclusion (a fork is genuinely exclusive) or no-preemption (Python
won't let you steal a lock), so every practical fix targets conditions 2 or 4.

---

### 25. How do you test threaded code?

**Assert on invariants, never on ordering.**

```python
assert sorted(results) == expected      # not: results == expected
assert counter.value == n * iterations  # conservation
assert len(connections) <= pool_size    # a bound
```

**To surface races:** crank up iteration counts, use more threads than cores,
`sys.setswitchinterval(0.000001)` to force constant preemption, add sleeps inside critical
sections to widen windows, and run the test 100× rather than once.

**To debug:** `logging` (thread-safe) with `%(threadName)s`, never `print`. Name your
threads. Install `threading.excepthook` so crashed workers aren't silent.
`faulthandler.dump_traceback_later()` or `py-spy dump` for hangs.

---

### 26. Your service's latency got worse after you added threads. Why?

Plausible causes, roughly in order:

1. **The work is CPU-bound** — the GIL serialises it and you've added switching overhead.
2. **Lock contention** — the critical section is too coarse, or you're doing I/O while
   holding a lock, so threads queue behind each other.
3. **Too many threads** — context-switching and memory pressure (~8 MB stack each);
   downstream services are throttling or queueing you.
4. **False sharing / GC pressure** from per-thread allocation.

How you'd confirm: profile (`py-spy top`), check whether threads are in `acquire()` vs
running, then measure with the pool size set to 1 as a baseline.

---

### 27. What is free-threaded Python?

PEP 703 — an official CPython build (experimental in 3.13, continuing in 3.14) with the GIL
removed, so threads execute bytecode genuinely in parallel. Trade-offs: some single-threaded
overhead, C extensions must be rebuilt and audited for thread safety, and **every race
condition in your code becomes far more likely** because operations that were incidentally
atomic under the GIL no longer are.

Check at runtime with `sys._is_gil_enabled()` (3.13+).

The takeaway to voice: "It doesn't make concurrency easier — it makes correct locking
matter more."

---

### 28. Design a multi-threaded web crawler.

Sketch this out loud:

- **Frontier**: `queue.Queue(maxsize=N)` of URLs — bounded for backpressure.
- **Workers**: `ThreadPoolExecutor`; I/O-bound, so ~32–64 threads, tuned to politeness
  limits rather than cores.
- **Seen set**: a `set` behind a `Lock`, checked-and-added atomically (check-then-act!).
- **Politeness**: a per-domain `Semaphore` for concurrency plus a token bucket for rate.
- **Retries**: exponential backoff **with jitter**, bounded attempts.
- **Shutdown**: `q.join()` to drain, then sentinels; cooperative `Event` for early abort.
- **Parsing**: CPU-bound — if it dominates, hand it to a `ProcessPoolExecutor`.
- **Observability**: named threads, structured logging, in-flight counters.

The details that mark experience: bounded queue, jittered retries, per-domain limits, and
having a real answer for shutdown.

---

## Things that make you sound senior

- "I'd measure whether it's actually I/O-bound before choosing."
- "`counter += 1` isn't atomic — the GIL doesn't make my invariants atomic, only individual
  bytecodes."
- "I'd use `ThreadPoolExecutor` rather than raw threads, so exceptions surface at
  `result()` instead of vanishing."
- "I'd give the queue a `maxsize` for backpressure."
- "Locks always in a consistent global order; never hold one across I/O."
- "There's no way to kill a thread — shutdown has to be cooperative, and I'd design that in
  from the start."
- "Ordering assertions in threaded tests are how you get a flaky suite. Assert invariants."
- "Retries need jitter, or every client retries in lockstep and stampedes the recovering
  service."

## Things that make you sound junior

- "Python threads make things faster." (Not for CPU work.)
- "The GIL makes Python thread-safe." (It does the opposite of what you think.)
- Using `time.sleep()` to synchronize instead of an `Event` or `Condition`.
- `if not q.empty(): q.get()` — a race, and `Queue` already blocks for you.
- `if` instead of `while` around `cond.wait()`.
- Believing `future.result(timeout=1)` cancels the task.
- Reaching for `multiprocessing` for an HTTP client, or threads for matrix math.
