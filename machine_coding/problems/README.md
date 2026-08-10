# Practice Problems

Six full machine coding problems, each a real round asked at product companies.

## How to run one

1. **Set a visible timer.** 120 min for problems 1–3, 90 min for 4–6.
2. Copy the skeleton: `cp -r ../toolkit/skeleton ~/practice/pN`
3. Write `NOTES.md` with your tiers **before any code**.
4. Build. `demo.py` running by minute 20. Stop coding at the 90% mark.
5. Verify: `python machine_coding/problems/check.py N --path ~/practice/pN`
6. Score yourself with [`../RUBRIC.md`](../RUBRIC.md). Be harsh.

```bash
python machine_coding/problems/check.py 1              # test your answer
python machine_coding/problems/check.py 1 --solution   # run the reference
python machine_coding/problems/check.py --solution     # all references
```

## The API contract rule

Each problem below specifies an **exact public API**. In a real round you'd design it
yourself — here it's fixed so the tests can run against your code. Everything *behind* that
API is your design, and that's what you're being scored on.

Put your solution in a single module named `solution.py` (or a package exporting the same
names) and point `check.py` at it with `--path`.

---

# Problem 1 — Rate Limiter

**Time: 120 min.** The most commonly asked machine coding problem in backend interviews.

> Design a rate limiter for an API gateway. Different endpoints need different limiting
> algorithms. Limits are **per client key** (user id, IP, API key). It will be called from
> many request threads at once.

### P0 — must work
- `TokenBucketLimiter(capacity, refill_rate, per=1.0)` — burst up to `capacity`, refills at
  `refill_rate` per `per` seconds
- `FixedWindowLimiter(limit, window)` — at most `limit` per fixed `window`-second bucket
- Both implement `allow(key: str) -> bool` — non-blocking, `True` if permitted
- Per-key isolation: exhausting key `"a"` must not affect key `"b"`
- Thread-safe

### P1 — if time
- `SlidingWindowLogLimiter(limit, window)` — exact sliding window, no boundary burst
- `RateLimiterService(factory)` — routes keys to per-key limiters created lazily by
  `factory()`; exposes `allow(key)` and `stats()`
- Memory cleanup: `RateLimiterService.evict_idle(older_than)` removes unused key state

### P2 — mention only
Distributed limiting via Redis, sliding-window-counter approximation, per-endpoint config.

### The API
```python
class RateLimiter(ABC):
    def allow(self, key: str) -> bool: ...

class TokenBucketLimiter(RateLimiter):
    def __init__(self, capacity: float, refill_rate: float, per: float = 1.0): ...

class FixedWindowLimiter(RateLimiter):
    def __init__(self, limit: int, window: float): ...

class SlidingWindowLogLimiter(RateLimiter):     # P1
    def __init__(self, limit: int, window: float): ...

class RateLimiterService:                        # P1
    def __init__(self, factory: Callable[[], RateLimiter]): ...
    def allow(self, key: str) -> bool: ...
    def stats(self) -> dict: ...                 # {"keys": n, "allowed": n, "denied": n}
    def evict_idle(self, older_than: float) -> int: ...
```

### What they're testing
The ABC is the whole point — three algorithms behind one interface. The concurrency trap is
the token refill: it's a read-modify-write on `(tokens, last_refill)` and must be atomic.
The design trap is a single global lock across all keys, which serialises unrelated clients.

**Say out loud:** *"Fixed window allows a 2× burst at the boundary — 100 requests at 0:59
and 100 more at 1:01. Sliding window log fixes that at the cost of storing timestamps."*

---

# Problem 2 — Pub/Sub Message Broker

**Time: 120 min.** Kafka-lite. Very common at Flipkart, Swiggy, Uber.

> Build an in-memory publish/subscribe broker. Publishers write to topics, subscribers read
> independently at their own pace. Each subscriber must see every message published after
> it subscribed, exactly in order.

### P0 — must work
- `create_topic(name)`, `publish(topic, payload) -> int` (returns offset)
- `subscribe(topic, subscriber_id)` — independent per-subscriber offset
- `poll(topic, subscriber_id, max_messages=10) -> list[Message]` — returns from the
  committed offset **without** advancing it
- `ack(topic, subscriber_id, offset)` — commits through `offset` (at-least-once delivery)
- Slow subscribers must not block fast ones, or publishers

### P1 — if time
- `subscribe_callback(topic, subscriber_id, callback)` — push delivery on a broker-owned
  worker thread; a raising callback must not kill the thread or affect others
- `unsubscribe(topic, subscriber_id)`
- Retention: `create_topic(name, max_messages=N)` drops the oldest beyond N
- `shutdown()` — stop all delivery threads cleanly

### P2 — mention only
Partitions and consumer groups, persistence, replication, dead-letter topics.

### The API
```python
class Broker:
    def __init__(self, n_delivery_workers: int = 2): ...
    def create_topic(self, name: str, max_messages: int | None = None) -> None: ...
    def publish(self, topic: str, payload: Any) -> int: ...
    def subscribe(self, topic: str, subscriber_id: str) -> None: ...
    def unsubscribe(self, topic: str, subscriber_id: str) -> None: ...
    def poll(self, topic: str, subscriber_id: str, max_messages: int = 10) -> list: ...
    def ack(self, topic: str, subscriber_id: str, offset: int) -> None: ...
    def subscribe_callback(self, topic, subscriber_id, callback) -> None: ...   # P1
    def stats(self) -> dict: ...
    def shutdown(self, timeout: float = 5.0) -> None: ...

@dataclass(frozen=True)
class Message:
    offset: int
    topic: str
    payload: Any
    timestamp: float
```

### What they're testing
Per-subscriber offsets are the core insight — the log is shared, the *cursors* are not.
The concurrency trap is holding the topic lock while invoking subscriber callbacks: a slow
or blocking subscriber then freezes the entire broker.

**Say out loud:** *"I copy the message batch under the lock and invoke callbacks outside it
— never run unknown code while holding a lock."*

---

# Problem 3 — Connection Pool

**Time: 120 min.**

> Build a thread-safe connection pool. Creating a connection is expensive, so reuse them.
> Cap the total. Callers that can't get one within a timeout should fail rather than hang.

### P0 — must work
- `acquire(timeout=None) -> Connection` — reuse idle, create up to `max_size`, block if
  exhausted, raise `PoolTimeoutError` on timeout
- `release(conn)` — return to the pool
- `connection()` context manager — releases even if the body raises
- Never exceed `max_size` connections in existence, under any interleaving
- `stats() -> {"in_use", "idle", "created", "max_size"}`

### P1 — if time
- `min_size` pre-warmed connections at construction
- Validation: a `validator(conn) -> bool` checked on acquire; invalid connections are
  discarded and replaced
- Idle reaping: connections idle longer than `max_idle_time` are closed by a background
  thread (never below `min_size`)
- `close()` — drain and close everything, reject further acquires

### P2 — mention only
Per-connection metrics, exponential backoff on creation failure, multiple pools by shard.

### The API
```python
class ConnectionPool:
    def __init__(self, factory, min_size=0, max_size=10, timeout=5.0,
                 max_idle_time=None, validator=None): ...
    def acquire(self, timeout=None): ...
    def release(self, conn) -> None: ...
    def connection(self): ...            # context manager
    def stats(self) -> dict: ...
    def close(self, timeout: float = 5.0) -> None: ...

class PoolTimeoutError(Exception): ...
class PoolClosedError(Exception): ...
```

### What they're testing
"Never exceed max_size" is a classic **check-then-act**: two threads both see `created < max`
and both create. Getting that atomic is the whole problem.

The other trap: creating the connection **while holding the lock**. Creation is slow I/O —
hold the lock only to reserve the slot, create outside it, and release the slot if creation
fails.

**Say out loud:** *"I reserve the slot under the lock, then create outside it, with a
try/except that gives the slot back if the factory raises — otherwise a failed creation
leaks capacity permanently."*

---

# Problem 4 — Key-Value Store with TTL

**Time: 90 min.** Redis-lite.

> An in-memory key-value store with per-key expiry. Expired keys must never be returned,
> and memory must actually be reclaimed — not just hidden.

### P0 — must work
- `set(key, value, ttl=None)`, `get(key) -> value | None`, `delete(key) -> bool`
- Expired keys are invisible to `get`, `exists`, `keys`, and `size` **immediately** on
  expiry, without waiting for a sweep
- Thread-safe

### P1 — if time
- Background sweeper thread that actually reclaims memory (`close()` stops it)
- `set(key, value, ttl, nx=True)` — set only if absent (atomic)
- `incr(key, by=1)` — atomic read-modify-write, creating at 0 if absent
- `get_or_set(key, factory, ttl=None)` — factory runs **exactly once** per key even under
  20 concurrent callers, and different keys must not block each other
- `stats() -> {"hits", "misses", "expired", "size"}`

### P2 — mention only
LRU eviction under a memory cap, persistence/AOF, key-space notifications.

### The API
```python
class KVStore:
    def __init__(self, sweep_interval: float = 0.5): ...
    def set(self, key, value, ttl=None, nx=False) -> bool: ...
    def get(self, key): ...
    def get_or_set(self, key, factory, ttl=None): ...
    def delete(self, key) -> bool: ...
    def exists(self, key) -> bool: ...
    def incr(self, key, by: int = 1) -> int: ...
    def ttl(self, key) -> float | None: ...
    def keys(self) -> list: ...
    def size(self) -> int: ...
    def stats(self) -> dict: ...
    def close(self, timeout: float = 5.0) -> None: ...
```

### What they're testing
**Lazy plus active expiry.** Lazy alone (check on read) never reclaims memory for keys
nobody reads. Active alone (sweeper) returns stale values between sweeps. You need both, and
knowing that is the point of the question.

`get_or_set` is the single-flight problem again: exactly-once per key, without a global lock
that serialises different keys.

---

# Problem 5 — Parking Lot

**Time: 90 min.** The single most-asked machine coding problem, period.

> Design a parking lot. Multiple floors, multiple spot sizes. Vehicles get a ticket on
> entry and pay on exit. Many entry and exit gates operate concurrently.

### P0 — must work
- Spot sizes `SMALL / MEDIUM / LARGE`; a vehicle fits its own size **or larger**
- `park(vehicle) -> Ticket`, raises `LotFullError` if nothing fits
- `unpark(ticket_id) -> Receipt` with a computed fee, frees the spot
- **A spot is never assigned to two vehicles.** This is the whole concurrency test.
- `availability() -> dict[SpotSize, int]`

### P1 — if time
- `PricingStrategy` interface — `HourlyPricing` and `FlatRatePricing` (this is the ABC hint)
- Multiple floors, with allocation preferring the lowest floor
- `find_vehicle(license_plate) -> SpotId | None`
- Reject duplicate parking of the same plate

### P2 — mention only
Reservations, EV charging spots, license plate recognition, payment gateway.

### The API
```python
class SpotSize(IntEnum):  SMALL = 1; MEDIUM = 2; LARGE = 3

@dataclass(frozen=True)
class Vehicle:      license_plate: str; size: SpotSize
@dataclass(frozen=True)
class Ticket:       id: str; license_plate: str; spot_id: str; floor: int; entry_time: float
@dataclass(frozen=True)
class Receipt:      ticket_id: str; spot_id: str; duration_seconds: float; fee: float

class ParkingLot:
    def __init__(self, layout: dict, pricing=None): ...
        # layout: {floor_number: {SpotSize.SMALL: count, ...}}
    def park(self, vehicle: Vehicle) -> Ticket: ...
    def unpark(self, ticket_id: str) -> Receipt: ...
    def availability(self) -> dict: ...
    def find_vehicle(self, license_plate: str): ...

class PricingStrategy(ABC):
    def compute(self, size: SpotSize, duration_seconds: float) -> float: ...

class LotFullError(Exception): ...
class TicketNotFoundError(Exception): ...
```

### What they're testing
Allocation is check-then-act: *find* a free spot, then *claim* it. Split those across two
lock acquisitions and two cars get the same spot. The test hammers `park()` from 20 threads
against 10 spots and asserts no spot is double-assigned and exactly 10 succeed.

Most candidates model this well and then bolt on a single global lock at the end. Put the
lock in from the first minute.

---

# Problem 6 — Concurrent Web Crawler

**Time: 90 min.** The hardest concurrency shape here.

> Crawl a set of seed URLs with a worker pool. Follow links up to a depth limit. Never fetch
> the same URL twice. Stop cleanly when there's nothing left to crawl.

### P0 — must work
- `crawl(seed_urls) -> CrawlResult` — blocks until finished, returns pages and errors
- N worker threads fetch concurrently
- Each URL fetched **at most once**, even when many pages link to it
- Respect `max_depth` and `max_pages`
- **Terminates cleanly** — the hard part, see below

### P1 — if time
- Politeness: per-domain rate limiting and a per-domain concurrency cap
- Retries with exponential backoff on transient fetch failures
- `on_page` progress callback, invoked outside any lock
- Cancellation: `stop()` from another thread ends the crawl promptly

### P2 — mention only
robots.txt, URL canonicalisation, persistent frontier, distributed crawling.

### The API
```python
@dataclass
class CrawlResult:
    pages: dict          # url -> content
    errors: dict         # url -> error string
    depth_of: dict       # url -> depth at which it was found
    fetched: int
    skipped: int

class Crawler:
    def __init__(self, fetcher, n_workers=4, max_depth=2, max_pages=100,
                 max_retries=0, rate_per_second=None, on_page=None): ...
    def crawl(self, seed_urls: list[str]) -> CrawlResult: ...
    def stop(self) -> None: ...
```
`fetcher(url) -> (content: str, links: list[str])`, and may raise.

### What they're testing

**Termination detection.** This is the interesting part, and most candidates get it wrong.

You cannot stop when the queue is empty — a worker may be mid-fetch and about to enqueue ten
more URLs. You cannot stop when all workers are idle either, unless you check that
*atomically together with* the queue being empty.

The two correct answers:
1. `queue.Queue` + `task_done()` + `q.join()` — the unfinished-task counter already tracks
   "dequeued but not yet complete". Enqueue children **before** calling `task_done()` on the
   parent. This is the elegant answer.
2. An explicit `active_workers` counter guarded by a `Condition`; the crawl ends when
   `active == 0 and queue.empty()`, checked under the same lock.

**Say out loud:** *"Termination isn't 'queue is empty' — a busy worker can still produce
work. I'm using `task_done`/`join` so the unfinished counter covers in-flight items."*

The dedup is also check-then-act: `if url not in seen: seen.add(url)` must be one atomic
step, or two workers both fetch it.

---

## Suggested order

| Week | Problems | Clock | Focus |
|---|---|---|---|
| 1 | Re-type the [worked example](../worked_example/) twice | untimed | learn the shape |
| 2 | 5 (parking lot), 1 (rate limiter), 4 (kv store) | 120 min | scoping and structure |
| 3 | 3 (pool), 2 (broker), 6 (crawler) | 90 min | harder concurrency |
| 4 | redo problem 5 cold | 90 min | feel the difference |

Problem 5 first is deliberate: it's the most commonly asked and the least concurrency-tricky,
so it's the gentlest place to practise the *process* before the problems get hard.
