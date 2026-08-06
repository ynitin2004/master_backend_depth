# Python Multithreading — Zero to Mastery

A complete, runnable course. Every concept has a **working example you run first**, then
**exercises you solve yourself**.

- Python here: **3.12.4** (standard GIL build)
- Everything is local. No installs, no internet. Standard library only.

## How to use this

Work top to bottom. For each module:

1. **Read** the section in this file.
2. **Run** the example: `python multithreading/examples/NN_name.py`
3. **Predict** the output *before* you run it. Being wrong is the lesson.
4. Only after finishing Modules 1–14, open [exercises/README.md](exercises/README.md).

Run everything from the repo root (`master_backend_depth`).

```bash
python multithreading/examples/01_first_thread.py
```

## Map

| # | Module | Example file |
|---|--------|-------------|
| 0 | Mental model: concurrency, parallelism, the GIL | — |
| 1 | Your first thread | `01_first_thread.py` |
| 2 | Thread lifecycle, join, daemon threads | `02_lifecycle_join_daemon.py` |
| 3 | Subclassing `Thread`, getting results back | `03_subclass_and_results.py` |
| 4 | Race conditions — seeing corruption with your own eyes | `04_race_condition.py` |
| 5 | `Lock` and `RLock` | `05_lock_and_rlock.py` |
| 6 | `Semaphore` — limiting concurrency | `06_semaphore.py` |
| 7 | `Event` — signalling between threads | `07_event.py` |
| 8 | `Condition` — wait for a state change | `08_condition.py` |
| 9 | `Barrier`, `Timer`, `local()` | `09_barrier_timer_local.py` |
| 10 | `queue.Queue` — the producer/consumer workhorse | `10_queue_producer_consumer.py` |
| 11 | Deadlock: cause and cure | `11_deadlock.py` |
| 12 | `ThreadPoolExecutor` and futures — what you'll actually use | `12_thread_pool_executor.py` |
| 13 | The GIL, measured: CPU-bound vs I/O-bound | `13_gil_benchmark.py` |
| 14 | Threads vs processes vs asyncio — choosing correctly | `14_threads_vs_processes_vs_async.py` |
| 15 | Real-world patterns (pool, fan-out/in, rate limiter, timeout, cancellation) | `15_patterns.py` |
| 16 | Testing & debugging threaded code | `16_debugging.py` |

Then: **[Practice problems](exercises/README.md)** (15 problems, progressive) and
**[Interview Q&A](INTERVIEW_QA.md)**.

---

# Module 0 — The mental model

Everything else makes sense only if this part lands. Read it slowly.

## A process vs a thread

A **process** is a running program. It owns its own memory. Two processes cannot see each
other's variables.

A **thread** is a path of execution *inside* a process. One process can have many threads,
and **they all share the same memory**. Your global variables, your objects, your lists —
every thread sees the same ones.

```
PROCESS (own memory: heap, globals, open files)
├── Thread 1 ── own call stack, own local variables
├── Thread 2 ── own call stack, own local variables
└── Thread 3 ── own call stack, own local variables
        ▲
        └── all three share the heap/globals
```

That sharing is the entire point of threads, and also the entire source of pain. Shared
memory means fast communication (just assign a variable) and it means two threads can
scribble on the same object at the same time and corrupt it.

**Rule of thumb:** locals are private, everything reachable from more than one thread is
dangerous.

## Concurrency vs parallelism

These are *not* synonyms, and interviewers ask this constantly.

- **Concurrency** = dealing with many things at once. Tasks are *in progress* over the same
  period; they may interleave on one CPU core. It's a structuring concept.
- **Parallelism** = doing many things at once, literally, on multiple cores at the same
  instant. It's an execution concept.

> One cook switching between chopping, stirring, and watching the oven is *concurrent*.
> Three cooks each doing one job simultaneously is *parallel*.

Python threads give you **concurrency always**, and **parallelism only for the right kind
of work** — which brings us to the GIL.

## The GIL (Global Interpreter Lock)

CPython (the Python you're running) has one mutex called the **GIL**. To execute Python
bytecode, a thread must hold the GIL. **Only one thread holds it at a time.**

Consequence: **two Python threads never run Python bytecode simultaneously.** Ten threads
crunching numbers on a 10-core machine will not go 10× faster. They'll go slightly *slower*
than one thread, because of switching overhead.

So why do threads help at all? Because the GIL is **released** whenever a thread does
something that isn't running Python bytecode:

- Waiting on a network socket (`requests.get`, DB query, API call)
- Reading/writing a file or disk
- `time.sleep()`
- Waiting on a lock
- Inside many C extensions (NumPy heavy math, compression, hashing, image decode)

While thread A is blocked waiting on the network, it drops the GIL and thread B runs. That
is where all the speedup comes from.

### The one line to remember

| Workload | Bottleneck | Use |
|---|---|---|
| **I/O-bound** — HTTP calls, DB, disk, sockets | waiting | **threads** (or asyncio) ✅ |
| **CPU-bound** — math, parsing, compression, ML in pure Python | CPU cycles | **processes** ✅ (threads don't help) |

Module 13 makes you *measure* this rather than take my word for it.

### Two important nuances

1. **The GIL does not make your code thread-safe.** `counter += 1` is three bytecodes
   (load, add, store); a thread switch can land in the middle. Module 4 shows the
   corruption live. People confuse "only one thread runs at a time" with "operations are
   atomic" — they're not.
2. **Free-threaded Python.** Python 3.13 introduced an official experimental *free-threaded*
   build (PEP 703) with no GIL, and 3.14 continued that work. On such a build, CPU-bound
   threads genuinely run in parallel — but every race condition in this course becomes
   *more* likely, not less. You are on a standard GIL build (3.12.4), so the classic rules
   apply. Check at runtime with `sys._is_gil_enabled()` (3.13+).

## When a thread switch can happen

The interpreter switches threads roughly every 5 ms by default
(`sys.getswitchinterval()`), or immediately when a thread blocks on I/O. You do **not**
control when. Assume a switch can happen between *any* two bytecodes. All correctness must
come from explicit synchronization, never from "it's probably fast enough."

---

# Module 1 — Your first thread

▶ `python multithreading/examples/01_first_thread.py`

The core API is `threading.Thread`:

```python
import threading

def worker(name, count):
    for i in range(count):
        print(f"{name}: {i}")

t = threading.Thread(target=worker, args=("A", 3))
t.start()   # spawns the OS thread, calls worker("A", 3) in it
t.join()    # blocks the CALLER until t finishes
```

Four things that matter:

- `target` — the callable to run. **Pass the function, don't call it.**
  `target=worker` ✅ — `target=worker()` ❌ (that runs it right now on the main thread).
- `args` / `kwargs` — arguments for the target. `args` must be a tuple:
  `args=("A",)` — the trailing comma is not optional.
- `start()` — begins execution. Calling `start()` twice raises `RuntimeError`.
  A `Thread` object is **not reusable**; make a new one.
- `join()` — wait for it to finish. `join(timeout=2)` waits at most 2 seconds; it does
  **not** kill the thread, it just stops waiting. Check `t.is_alive()` after to see which
  happened.

`run()` vs `start()`: calling `t.run()` directly just executes the function on the current
thread — no new thread at all. This is a classic interview trap.

## Interleaving is not deterministic

Two threads printing will interleave differently across runs. If your code's correctness
depends on the ordering you saw once, it is broken.

---

# Module 2 — Lifecycle, join, and daemon threads

▶ `python multithreading/examples/02_lifecycle_join_daemon.py`

```
Thread()  ──start()──▶  runnable ⇄ running  ──target returns──▶  dead
   │                          │                                     │
 is_alive() False        is_alive() True                      is_alive() False
                                                              join() returns instantly
```

Useful introspection:

```python
threading.current_thread().name   # who am I
threading.main_thread()           # the main thread object
threading.active_count()          # how many alive right now
threading.enumerate()             # list of alive Thread objects
threading.get_ident()             # OS-level thread id
```

## Daemon threads

```python
t = threading.Thread(target=loop, daemon=True)
```

- **Non-daemon (default):** the interpreter waits for it before exiting.
- **Daemon:** the interpreter **kills it abruptly at exit** — no cleanup, no `finally`
  blocks guaranteed, mid-write files may be truncated.

Use daemons for background chores where an abrupt death is harmless (heartbeat, metrics
poller). **Never** for anything holding a resource or writing data. `daemon` must be set
*before* `start()`.

## There is no `thread.kill()`

Python gives you no way to forcibly stop a thread, by design — killing a thread holding a
lock would deadlock the process. The only correct pattern is **cooperative cancellation**:
the thread checks a flag or an `Event` and returns on its own.

```python
stop = threading.Event()
def worker():
    while not stop.is_set():
        do_a_chunk()
stop.set()   # ask it to stop
t.join()     # wait for it to actually stop
```

Long `sleep`s inside a worker should be `stop.wait(5)` instead of `time.sleep(5)` — it
returns early the instant you signal, so shutdown is fast.

---

# Module 3 — Subclassing `Thread`, and getting results back

▶ `python multithreading/examples/03_subclass_and_results.py`

Subclass when the thread has state or needs its own methods. Override **`run`**, and call
`super().__init__()` first.

```python
class Worker(threading.Thread):
    def __init__(self, url):
        super().__init__()          # required, forget it and you get RuntimeError
        self.url = url
        self.result = None
    def run(self):                  # override run, still call start()
        self.result = fetch(self.url)
```

## `target` returns are thrown away

`t.start()` gives you nothing back; the return value of `target` is discarded. Three ways
to collect results:

1. **Store on the instance** (`self.result`) — read it *after* `join()`.
2. **Push to a `queue.Queue`** — thread-safe, works with any number of producers.
3. **`ThreadPoolExecutor` + futures** (Module 12) — the modern answer, and what you should
   reach for by default.

## Exceptions vanish too

An exception inside a thread does **not** propagate to the caller. It prints a traceback
and the thread dies; the main thread notices nothing. Either catch it inside the thread and
store it, or use `ThreadPoolExecutor`, whose `future.result()` re-raises it in the caller.
(`threading.excepthook` lets you install a global handler.)

---

# Module 4 — Race conditions

▶ `python multithreading/examples/04_race_condition.py`

This is the module to actually run. Two threads each increment a global 200,000 times. The
correct answer is 400,000. You will get less.

```python
counter += 1
```

compiles to roughly:

```
LOAD  counter    # read 41
ADD   1          # compute 42
STORE counter    # write 42
```

If both threads read 41 before either stores, both store 42. One increment is lost forever.

**Race condition:** the result depends on the unpredictable timing of threads.
**Critical section:** the region of code that must not be entered by two threads at once.

The example also shows a **check-then-act** race (`if key not in d: d[key] = ...`), which
is the same bug wearing a different hat and is far more common in real code than counters.

### What *is* atomic?

Some single-bytecode operations are effectively atomic under the GIL (`list.append`,
`dict[k] = v`, `x = y`). Relying on this is a bad habit: the guarantee is a CPython
implementation detail, it evaporates the moment you need *two* operations to be atomic
together, and it does not hold on free-threaded builds. **Use a lock.**

---

# Module 5 — `Lock` and `RLock`

▶ `python multithreading/examples/05_lock_and_rlock.py`

A **mutex**: only one thread at a time may hold it.

```python
lock = threading.Lock()

with lock:            # always prefer the with-statement
    counter += 1      # critical section
```

`with` guarantees release even if the body raises. The manual form
(`lock.acquire()` / `try: ... finally: lock.release()`) is equivalent but easier to get
wrong — a missed `release()` hangs your program forever.

Options: `lock.acquire(blocking=False)` returns `False` immediately instead of waiting;
`lock.acquire(timeout=2)` gives up after 2 s. Both let you avoid blocking indefinitely.

## `Lock` vs `RLock`

`Lock` is **not reentrant**. If the thread holding it tries to acquire it again — commonly
because one locked method calls another locked method — it deadlocks against *itself*.

`RLock` (reentrant lock) may be acquired multiple times **by the same thread**, and must be
released the same number of times. It's what you want for recursive or nested-method
locking.

## Granularity

Hold the lock for as *little* code as possible. Never do I/O, `sleep`, or call unknown
code while holding one — you serialize the whole program and invite deadlock. Compute
outside, mutate inside.

---

# Module 6 — `Semaphore`

▶ `python multithreading/examples/06_semaphore.py`

A counter-based lock: allows **N** threads in at once, not just one.

```python
sem = threading.Semaphore(3)     # at most 3 concurrent
with sem:
    hit_the_api()
```

Use it to cap concurrent DB connections, API calls, or file handles — the classic
"connection pool" limiter. `Lock` is essentially `Semaphore(1)` (with an ownership
difference: a `Lock` can be released by any thread, and a semaphore's count can rise above
its start value if over-released — `BoundedSemaphore` raises `ValueError` instead, which is
what you want to catch that bug).

---

# Module 7 — `Event`

▶ `python multithreading/examples/07_event.py`

A one-bit flag threads can wait on. The simplest signalling primitive.

```python
ready = threading.Event()

# waiters
ready.wait()            # blocks until set; returns immediately after
ready.wait(timeout=5)   # returns True if set, False if timed out

# signaller
ready.set()             # wake ALL waiters
ready.clear()           # back to unset
ready.is_set()
```

Two canonical uses: **startup gate** (workers wait until config is loaded) and **shutdown
signal** (the cooperative-cancellation pattern from Module 2). `set()` releases *every*
waiter, which is what makes it different from a lock.

---

# Module 8 — `Condition`

▶ `python multithreading/examples/08_condition.py`

Use when threads must wait for an **arbitrary state change**, not just a one-shot flag.
A `Condition` bundles a lock with a waiting room.

```python
cond = threading.Condition()

# consumer
with cond:
    while not items:            # ALWAYS a while loop, never if
        cond.wait()             # atomically releases the lock and sleeps
    item = items.pop()

# producer
with cond:
    items.append(x)
    cond.notify()               # wake one waiter (notify_all() wakes all)
```

Three rules people get wrong:

1. **`wait()` must be inside `while`, not `if`.** On waking, the state may have already
   been consumed by another thread (and *spurious wakeups* are permitted). Recheck.
2. `wait()` **releases the lock while sleeping** and re-acquires it before returning. This
   is why it can't deadlock with the producer.
3. You must **hold the lock** to call `wait()` or `notify()`.

`cond.wait_for(predicate)` is the tidy shorthand for the while-loop.

---

# Module 9 — `Barrier`, `Timer`, `local()`

▶ `python multithreading/examples/09_barrier_timer_local.py`

**`Barrier(n)`** — a rendezvous. Every thread calls `barrier.wait()` and *all* block until
the n-th arrives, then all release together. For phased/lock-step work (parallel simulation
steps, "all workers must finish loading before any starts querying"). If a thread dies
while others wait, the barrier goes "broken" and everyone gets `BrokenBarrierError` rather
than hanging forever.

**`Timer(interval, fn)`** — a Thread that runs `fn` after a delay. `cancel()` stops it if it
hasn't fired. Re-arm it inside itself for a repeating job.

**`threading.local()`** — an object whose attributes are **per-thread**. Each thread sees
its own values, same variable name. Perfect for per-thread DB connections, request IDs, or
non-thread-safe client objects: you get isolation without passing state through every
function signature.

---

# Module 10 — `queue.Queue`: the producer/consumer workhorse

▶ `python multithreading/examples/10_queue_producer_consumer.py`

**This is the most important practical module in the course.** `queue.Queue` is already
thread-safe — internally it uses locks and conditions so you don't have to. Most real
threading code is producers pushing work and consumers pulling it.

```python
import queue
q = queue.Queue(maxsize=10)     # maxsize=0 means unbounded

q.put(item)                     # blocks if full
item = q.get()                  # blocks if empty
q.task_done()                   # mark the item finished
q.join()                        # block until every put() item is task_done()
```

`maxsize` gives you **backpressure**: a fast producer can't blow up memory because `put()`
blocks once the queue is full. Set it.

## Shutting consumers down: the sentinel

Consumers sit in `while True: q.get()` and will block forever. Push one sentinel per
consumer:

```python
SENTINEL = object()
for _ in range(n_workers):
    q.put(SENTINEL)
```

Each worker sees one, breaks its loop, and exits. (`put` it back if workers share, or just
send exactly N.)

Also in the example: `LifoQueue` (a stack), `PriorityQueue` (pops smallest first — push
`(priority, item)` tuples; add a tiebreaker counter so it never has to compare the items
themselves), and non-blocking `get_nowait()` / `put_nowait()` with `queue.Empty` /
`queue.Full`.

---

# Module 11 — Deadlock

▶ `python multithreading/examples/11_deadlock.py`

Two threads, two locks, opposite order:

```
Thread A: holds lock1 ─ wants lock2 ──┐
                                      ├── neither can ever proceed
Thread B: holds lock2 ─ wants lock1 ──┘
```

Deadlock needs all four **Coffman conditions** simultaneously: mutual exclusion, hold-and-
wait, no preemption, circular wait. Break any one and it's impossible.

Practical cures, in order of preference:

1. **Global lock ordering** — every thread acquires locks in the same fixed order (e.g. by
   `id(lock)` or account number). Kills the circular wait. This is the standard fix.
2. **`acquire(timeout=...)`** — give up, release what you hold, back off, retry.
3. **Hold one lock at a time**, or use a single coarser lock.

The example runs the deadlock in daemon threads with a timeout so your terminal doesn't
hang, then shows the ordered fix, then the timeout fix.

Related: **livelock** (threads keep responding to each other, no progress),
**starvation** (one thread never gets the lock).

---

# Module 12 — `ThreadPoolExecutor` and futures

▶ `python multithreading/examples/12_thread_pool_executor.py`

**This is what you should actually write in production code.** `concurrent.futures` is the
high-level API: you hand it work, it manages threads, it gives you results and exceptions
properly.

```python
from concurrent.futures import ThreadPoolExecutor, as_completed

with ThreadPoolExecutor(max_workers=8) as pool:       # __exit__ waits for all
    futures = {pool.submit(fetch, url): url for url in urls}
    for fut in as_completed(futures):                 # yields in COMPLETION order
        url = futures[fut]
        try:
            data = fut.result()                       # re-raises worker exceptions HERE
        except Exception as e:
            print(f"{url} failed: {e}")
```

Key API:

- `submit(fn, *args)` → a `Future`, immediately. Non-blocking.
- `future.result(timeout=None)` — blocks; returns the value **or re-raises the exception**.
- `future.exception()`, `.done()`, `.cancel()` (only works if not yet started).
- `pool.map(fn, iterable)` — like `map`, results in **input order**, raises on first error
  when you iterate. Simpler; less control.
- `as_completed(futures)` — iterate as results land. Best for "show progress" / fail fast.
- `with` block calls `shutdown(wait=True)`. Use `pool.shutdown(wait=False, cancel_futures=True)`
  to bail early.

**Sizing `max_workers`:** I/O-bound → far more than your core count is fine (32, 64…);
tune against the *remote* service's limits, not your CPU's. CPU-bound → use
`ProcessPoolExecutor` instead.

The one real gotcha: **a raised exception is silent until you call `.result()`.** If you
submit and never look at the future, errors disappear.

---

# Module 13 — The GIL, measured

▶ `python multithreading/examples/13_gil_benchmark.py`

Don't trust the theory — this benchmarks it on your machine:

- CPU-bound work, 1 thread vs 4 threads → **no speedup** (often slightly worse).
- CPU-bound work, 4 *processes* → **real speedup**, roughly ×cores.
- I/O-bound work (simulated latency), 1 thread vs 8 threads → **large speedup**, near-linear.

Run it and read the numbers off your own CPU. That table is the answer to half of all
threading interview questions, and now you'll have measured it rather than memorized it.

---

# Module 14 — Threads vs processes vs asyncio

▶ `python multithreading/examples/14_threads_vs_processes_vs_async.py`

| | Threads | Processes | asyncio |
|---|---|---|---|
| Memory | shared | separate (pickled IPC) | shared |
| Best for | I/O-bound | CPU-bound | very high-concurrency I/O |
| Parallel CPU? | ❌ (GIL) | ✅ | ❌ |
| Cost per unit | ~MBs stack | heavy (new interpreter) | ~KBs |
| Practical scale | hundreds | ~cores | tens of thousands |
| Switch points | anywhere (preemptive) | n/a | only at `await` (cooperative) |
| Danger | races, deadlocks | pickling, startup cost | one blocking call stalls everything |

Notes worth knowing:

- **Windows** (you) uses `spawn` for multiprocessing: children re-import your module, so
  `if __name__ == "__main__":` is **mandatory** or you fork-bomb yourself. Args must be
  picklable.
- Bridging the two worlds: `await asyncio.to_thread(blocking_fn)` runs blocking code off
  the event loop; `loop.run_in_executor(pool, fn)` is the older equivalent.
- Choose: **CPU-bound → processes. I/O-bound with blocking libraries → threads. I/O-bound,
  huge fan-out, async libraries available → asyncio.**

---

# Module 15 — Patterns you'll actually write

▶ `python multithreading/examples/15_patterns.py`

- **Worker pool** with a shared queue and graceful shutdown
- **Fan-out / fan-in** — split work, merge results, preserve order
- **Thread-safe counter / cache** — lock-wrapped class, and the double-checked-locking
  singleton
- **Rate limiter** — N calls per second across all threads
- **Timeouts** — `future.result(timeout=…)` and why the work keeps running anyway
- **Cooperative cancellation** — `Event`-driven shutdown that's actually prompt
- **Retry with backoff** inside a pooled worker

---

# Module 16 — Testing and debugging threaded code

▶ `python multithreading/examples/16_debugging.py`

- Races are **timing-dependent**: they pass 99 times and fail in production. Amplify them
  with `sys.setswitchinterval(0.000001)`, sleeps inside critical sections, and high
  iteration counts — then run the test many times.
- `print()` from threads interleaves badly. Use `logging` — it's thread-safe and
  `%(threadName)s` tells you who said what.
- Name your threads (`Thread(name="poller-3")`). Anonymous `Thread-7` is useless in a log.
- Hung process? `faulthandler.dump_traceback_later(10)` prints every thread's stack, or
  send it a signal with `faulthandler.register`. `threading.enumerate()` tells you who's
  still alive.
- `threading.excepthook` catches exceptions that would otherwise die silently in a thread.
- Determinism: assert on *invariants* (final total, set of results), never on ordering.

---

# Cheat sheet

```python
import threading, queue
from concurrent.futures import ThreadPoolExecutor, as_completed

# --- create ---
t = threading.Thread(target=fn, args=(1,), kwargs={}, name="w1", daemon=False)
t.start(); t.join(timeout=None); t.is_alive()

# --- mutual exclusion ---
lock  = threading.Lock()        # one holder; not reentrant
rlock = threading.RLock()       # same thread may re-acquire
sem   = threading.Semaphore(5)  # up to 5 holders
with lock: ...                  # always prefer `with`

# --- signalling ---
ev = threading.Event(); ev.set(); ev.clear(); ev.wait(timeout=1); ev.is_set()
cond = threading.Condition()
with cond:
    cond.wait_for(lambda: ready)     # while-loop done for you
    cond.notify() / cond.notify_all()
b = threading.Barrier(4); b.wait()

# --- per-thread state ---
tl = threading.local(); tl.conn = connect()

# --- queues ---
q = queue.Queue(maxsize=100)     # also LifoQueue, PriorityQueue
q.put(x); q.get(); q.task_done(); q.join()
q.get_nowait()                   # raises queue.Empty

# --- the one you'll use most ---
with ThreadPoolExecutor(max_workers=16) as pool:
    for f in as_completed([pool.submit(fn, x) for x in xs]):
        f.result()               # re-raises worker exceptions

# --- introspection ---
threading.current_thread().name, threading.active_count(), threading.enumerate()
```

## The ten rules

1. I/O-bound → threads. CPU-bound → processes.
2. Shared mutable state needs a lock. Every time. No exceptions for "it's just an int."
3. Always `with lock:`, never bare `acquire()`.
4. Hold locks briefly. Never do I/O or call unknown code while holding one.
5. Acquire multiple locks in a globally consistent order.
6. `Condition.wait()` goes in a `while`, never an `if`.
7. You cannot kill a thread. Design cooperative shutdown from the start.
8. Daemon threads die abruptly — never let them own data or resources.
9. Prefer `queue.Queue` and `ThreadPoolExecutor` over hand-rolled locking.
10. Check `future.result()` or your exceptions disappear.

---

Next: **[exercises/README.md](exercises/README.md)** — 15 problems, easy → hard, with full
solutions and self-checking tests.
