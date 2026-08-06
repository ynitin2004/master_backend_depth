# Practice Problems — 15 problems, easy → interview-hard

**Do the examples first.** These assume you've run `multithreading/examples/01`–`16`.

## How this works

Each problem has a starter file in `exercises/` with a `TODO`. Write your solution there,
then check it:

```bash
python multithreading/exercises/check.py 3          # check problem 3
python multithreading/exercises/check.py            # check all
python multithreading/exercises/check.py 3 --solution   # run the reference solution
```

The checker runs each solution many times with an aggressive thread-switch interval, so a
"works on my machine" race will be caught.

**Look at `solutions/` only after you've had a real attempt.** Reading a threading solution
teaches you almost nothing; debugging your own deadlock teaches you everything.

---

## Tier 1 — Basics (Modules 1–3)

### Problem 1 — Parallel sum
`ex01_parallel_sum.py`

Given a list of 1,000,000 integers, split it into `n` chunks and sum each chunk in its own
thread. Return the total.

- Must use raw `threading.Thread` (not a pool).
- Must return the correct total every time.
- Signature: `parallel_sum(numbers: list[int], n_threads: int = 4) -> int`

*Tests:* correctness for various `n_threads`, including `n_threads=1` and a list shorter
than `n_threads`.

**Thinking point:** will this be *faster* than `sum(numbers)`? Why not? (Module 13.)

---

### Problem 2 — Ordered downloader
`ex02_ordered_results.py`

`fetch(url)` is given to you (it sleeps a random amount, then returns a string). Fetch a
list of URLs concurrently — one thread each — and return results **in the same order as the
input list**.

- Signature: `fetch_all(urls: list[str]) -> list[str]`
- No `concurrent.futures` for this one. Raw threads.

**Thinking point:** two ways to do this. One uses a pre-sized list, one uses a queue of
`(index, result)`. Which needs a lock and which doesn't?

---

### Problem 3 — Thread-safe counter
`ex03_safe_counter.py`

Implement `SafeCounter` with `increment()`, `decrement()`, `value`, and
`increment_if_below(limit)` which increments **only if** the current value is `< limit`,
returning `True`/`False`.

- 50 threads × 1000 operations must give the exact right answer.
- `increment_if_below` must never let the counter exceed the limit — this is a
  check-then-act, so the check and the increment have to be one atomic unit.

---

## Tier 2 — Synchronization (Modules 4–9)

### Problem 4 — Fix the buggy bank
`ex04_fix_the_bank.py`

The file contains a `Bank` class with **three separate concurrency bugs**. Find and fix all
three without changing the public API.

The bugs (don't peek at the answers, but here are their categories):
1. A lost-update race.
2. A check-then-act race that allows an overdraft.
3. A deadlock in `transfer`.

*Tests:* money is conserved, no account goes negative, and 200 concurrent transfers
complete within 10 seconds (i.e. no deadlock).

---

### Problem 5 — Bounded blocking queue
`ex05_bounded_queue.py`

Implement `BoundedQueue(maxsize)` **from scratch** using only `threading.Condition` — no
`queue` module.

- `put(item)` blocks while full, `get()` blocks while empty.
- `put(item, timeout=…)` and `get(timeout=…)` raise `TimeoutError` on expiry.
- Must work with many producers and many consumers simultaneously.

**This is the single most common "write me a concurrency primitive" interview question.**
Get it right without looking.

**Thinking point:** why must the waits be `while` loops? Why `notify_all` and not `notify`?

---

### Problem 6 — Rate-limited crawler
`ex06_rate_limiter.py`

Implement `crawl(urls, max_concurrent, calls_per_second)`:
- at most `max_concurrent` requests in flight at any moment (`Semaphore`)
- at most `calls_per_second` started in any 1-second window (token bucket)

*Tests:* the checker records timestamps and asserts both limits held.

---

### Problem 7 — Print in order
`ex07_print_in_order.py`

Three threads run `first()`, `second()`, `third()` — started in random order. Make the
output always be `first second third`.

Then do it a second way: `print_numbers(n)` with three threads printing `1,2,3,…,n` in
strict round-robin (thread A prints 1, B prints 2, C prints 3, A prints 4…).

**Thinking point:** `Event` works for the first. For the second you want a `Condition` with
a turn variable — this is the classic "zero-even-odd" family of interview problems.

---

### Problem 8 — Barrier-based simulation
`ex08_phased_simulation.py`

`n` workers each run `k` phases. No worker may start phase `i+1` until **all** workers have
finished phase `i`, and the aggregate for each phase must be computed exactly once between
phases.

*Tests:* asserts no worker ever ran ahead, and each phase's aggregate is correct.

---

## Tier 3 — Pools and pipelines (Modules 10–12)

### Problem 9 — Web scraper with retries
`ex09_scraper.py`

Using `ThreadPoolExecutor`, fetch 30 URLs where ~30% fail randomly.

- retry each failure up to 3 times with exponential backoff + jitter
- return `{"ok": {url: content}, "failed": {url: last_error}}`
- process results as they arrive (`as_completed`), not in a final batch
- the whole thing must never hang, even if every URL fails

---

### Problem 10 — Multi-stage pipeline
`ex10_pipeline.py`

Build a 3-stage pipeline joined by queues:

```
producer(s) -> [q1] -> parser(s) -> [q2] -> writer(s)
```

- different worker counts per stage (e.g. 1 producer, 4 parsers, 2 writers)
- bounded queues (backpressure)
- **clean shutdown**: every item processed exactly once, no worker left hanging, no
  sentinel lost

*Tests:* all 100 items reach the writer exactly once, and the process exits.

**This is the hardest one on shutdown correctness.** Sentinels must cascade stage by stage.

---

### Problem 11 — Parallel file search
`ex11_file_search.py`

Search a directory tree for files containing a pattern, using a thread pool.

- returns `[(path, line_number, line)]`
- must handle unreadable files without crashing a worker
- must be bounded (don't submit 100,000 futures at once)

**Thinking point:** is this I/O-bound or CPU-bound? Does the answer change if the regex is
complex? (Module 13.)

---

### Problem 12 — Single-flight cache
`ex12_single_flight.py`

`get(key)` returns a cached value, computing it via a slow `compute(key)` on a miss. If 20
threads request the same missing key at once, `compute` must be called **exactly once** for
that key — but requests for *different* keys must not block each other.

*Tests:* asserts `compute` call counts and asserts that 5 different keys are computed
concurrently (total time ≈ one compute, not five).

---

## Tier 4 — Interview-hard

### Problem 13 — Read-write lock
`ex13_rwlock.py`

Implement `ReadWriteLock`:
- many readers concurrently, **or** one writer exclusively
- `read_lock()` / `write_lock()` as context managers
- **no writer starvation**: a waiting writer must block *new* readers, so a continuous
  stream of readers can't starve it forever

*Tests:* asserts concurrent readers really overlap, that a writer is exclusive, and that a
writer eventually gets in under constant read load.

---

### Problem 14 — Dining philosophers
`ex14_dining_philosophers.py`

5 philosophers, 5 forks, each needs both neighbouring forks to eat. Make all of them eat
`k` times with **no deadlock and no starvation**.

Implement **two** different solutions:
1. Resource ordering (lowest-numbered fork first).
2. A limiting semaphore (at most 4 seated at once) *or* the asymmetric solution (odd
   philosophers pick up left first, even pick up right first).

*Tests:* everyone eats `k` times within the time limit.

---

### Problem 15 — Thread-safe LRU cache
`ex15_lru_cache.py`

`LRUCache(capacity)` with `get(key)` and `put(key, value)`, thread-safe, correct eviction
order under concurrency.

- `get` on a hit must count as a use (moves it to most-recent)
- `put` on a full cache evicts the least-recently-used
- must never exceed `capacity`, ever, under any interleaving
- report `hits` / `misses` / `evictions` accurately

**Thinking point:** `OrderedDict.move_to_end` makes the single-threaded version four lines.
Where exactly does the lock go, and why can't you use a plain `dict` + a separate list?

---

## After you finish

- Re-read the **ten rules** at the bottom of [../README.md](../README.md). They should all
  feel obvious now.
- Work through [../INTERVIEW_QA.md](../INTERVIEW_QA.md) — say the answers out loud.
- Then go back to problems 5, 10, 13, and 14 and write them again from a blank file. Those
  four are the ones that come up in interviews.
