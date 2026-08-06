"""
Self-checking test runner for the practice problems.

    python multithreading/exercises/check.py            # check all your answers
    python multithreading/exercises/check.py 5          # check problem 5
    python multithreading/exercises/check.py 5 --solution   # run the reference
    python multithreading/exercises/check.py --solution     # run all references

Tests run each solution repeatedly with an aggressive thread-switch interval,
so a "works on my machine" race gets caught.
"""

import glob
import importlib.util
import os
import random
import sys
import threading
import time

HERE = os.path.dirname(os.path.abspath(__file__))
SOLUTIONS = os.path.join(HERE, "solutions")


# --------------------------------------------------------------- infrastructure
def load(problem, use_solution):
    """Import the starter (or reference solution) for a problem number."""
    directory = SOLUTIONS if use_solution else HERE
    prefix = "sol" if use_solution else "ex"
    matches = glob.glob(os.path.join(directory, f"{prefix}{problem:02d}_*.py"))
    if not matches:
        raise FileNotFoundError(f"no {prefix}{problem:02d}_*.py in {directory}")

    spec = importlib.util.spec_from_file_location(f"p{problem}", matches[0])
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


class Failure(AssertionError):
    pass


def check(condition, message):
    if not condition:
        raise Failure(message)


def repeat(times):
    """Decorator: run the test body `times` times to shake out races."""
    def wrapper(fn):
        def inner(mod):
            original = sys.getswitchinterval()
            sys.setswitchinterval(0.000001)     # force constant preemption
            try:
                for _ in range(times):
                    fn(mod)
            finally:
                sys.setswitchinterval(original)
        inner.__name__ = fn.__name__
        return inner
    return wrapper


# ------------------------------------------------------------------- the tests
@repeat(5)
def test_01(mod):
    data = list(range(1, 100_001))
    expected = sum(data)
    for n in (1, 2, 4, 7, 16):
        check(mod.parallel_sum(data, n) == expected,
              f"parallel_sum(n_threads={n}) wrong")
    check(mod.parallel_sum([], 4) == 0, "empty list should be 0")
    check(mod.parallel_sum([5], 4) == 5, "list shorter than n_threads")
    check(mod.parallel_sum([1, 2, 3], 10) == 6, "n_threads > len(numbers)")


@repeat(3)
def test_02(mod):
    urls = [f"site{i}.com" for i in range(10)]
    t0 = time.perf_counter()
    out = mod.fetch_all(urls)
    elapsed = time.perf_counter() - t0

    check(out == [f"content-of-{u}" for u in urls],
          f"order not preserved: {out}")
    check(elapsed < 0.6, f"took {elapsed:.2f}s -- did it actually run concurrently? "
                         f"(sequential would be ~0.8s)")


@repeat(3)
def test_03(mod):
    c = mod.SafeCounter()
    threads = [threading.Thread(target=lambda: [c.increment() for _ in range(1000)])
               for _ in range(50)]
    for t in threads: t.start()
    for t in threads: t.join()
    check(c.value == 50_000, f"expected 50000, got {c.value}")

    c2 = mod.SafeCounter(100)
    threads = [threading.Thread(target=lambda: [c2.decrement() for _ in range(100)])
               for _ in range(10)]
    for t in threads: t.start()
    for t in threads: t.join()
    check(c2.value == -900, f"expected -900, got {c2.value}")

    # The real test: increment_if_below must never exceed the limit.
    c3 = mod.SafeCounter()
    successes = []
    s_lock = threading.Lock()

    def hammer():
        local = 0
        for _ in range(200):
            if c3.increment_if_below(500):
                local += 1
        with s_lock:
            successes.append(local)

    threads = [threading.Thread(target=hammer) for _ in range(20)]
    for t in threads: t.start()
    for t in threads: t.join()

    check(c3.value <= 500, f"counter exceeded the limit: {c3.value} > 500")
    check(c3.value == 500, f"expected exactly 500, got {c3.value}")
    check(sum(successes) == 500,
          f"increment_if_below returned True {sum(successes)} times, expected 500")


def test_04(mod):
    bank = mod.Bank(n_accounts=5, starting_balance=1000)
    start_total = bank.total_money()

    # Deposits + withdrawals: money must be conserved and never go negative.
    def churn():
        for _ in range(50):
            bank.deposit(random.randrange(5), 10)
            bank.withdraw(random.randrange(5), 10)

    threads = [threading.Thread(target=churn) for _ in range(8)]
    for t in threads: t.start()
    for t in threads: t.join(timeout=20)
    check(not any(t.is_alive() for t in threads), "deposit/withdraw deadlocked")
    check(bank.total_money() == start_total,
          f"BUG 1 (lost update): total went {start_total} -> {bank.total_money()}")

    # Overdraft test: 20 threads racing to drain one account.
    bank2 = mod.Bank(n_accounts=2, starting_balance=100)
    results = []
    r_lock = threading.Lock()

    def drain():
        got = bank2.withdraw(0, 100)
        with r_lock:
            results.append(got)

    threads = [threading.Thread(target=drain) for _ in range(20)]
    for t in threads: t.start()
    for t in threads: t.join(timeout=20)
    check(bank2.accounts[0].balance >= 0,
          f"BUG 2 (overdraft): balance went negative "
          f"({bank2.accounts[0].balance})")
    check(sum(results) == 1,
          f"BUG 2 (overdraft): {sum(results)} withdrawals succeeded, expected 1")

    # Deadlock test: 200 transfers in BOTH directions between the same pairs.
    bank3 = mod.Bank(n_accounts=5, starting_balance=1000)
    start_total = bank3.total_money()
    threads = []
    for i in range(200):
        a, b = i % 5, (i + 1) % 5
        if i % 2:
            a, b = b, a                       # opposite direction -> deadlock bait
        threads.append(threading.Thread(target=bank3.transfer, args=(a, b, 50)))

    t0 = time.perf_counter()
    for t in threads: t.start()
    for t in threads: t.join(timeout=10)
    elapsed = time.perf_counter() - t0

    stuck = sum(t.is_alive() for t in threads)
    check(stuck == 0, f"BUG 3 (deadlock): {stuck} threads still stuck after "
                      f"{elapsed:.1f}s")
    check(bank3.total_money() == start_total,
          f"money not conserved in transfers: {start_total} -> "
          f"{bank3.total_money()}")
    check(all(a.balance >= 0 for a in bank3.accounts.values()),
          "a transfer drove an account negative")


def test_05(mod):
    q = mod.BoundedQueue(3)
    check(q.qsize() == 0, "new queue should be empty")

    # Timeouts.
    try:
        q.get(timeout=0.05)
        raise Failure("get() on an empty queue should raise TimeoutError")
    except TimeoutError:
        pass

    for i in range(3):
        q.put(i)
    check(q.qsize() == 3, f"qsize should be 3, got {q.qsize()}")
    try:
        q.put(99, timeout=0.05)
        raise Failure("put() on a full queue should raise TimeoutError")
    except TimeoutError:
        pass
    check([q.get() for _ in range(3)] == [0, 1, 2], "queue is not FIFO")

    # Blocking behaviour: a put on a full queue must actually WAIT.
    q2 = mod.BoundedQueue(2)
    q2.put("a"); q2.put("b")
    order = []
    o_lock = threading.Lock()

    def putter():
        q2.put("c")                        # must block until the get() below
        with o_lock:
            order.append("put-returned")

    t = threading.Thread(target=putter)
    t.start()
    time.sleep(0.15)
    with o_lock:
        check("put-returned" not in order, "put() did not block on a full queue")
    q2.get()
    t.join(timeout=2)
    check(not t.is_alive(), "put() never unblocked after a get()")

    # Stress: 4 producers x 250 items, 4 consumers. Nothing lost or duplicated.
    q3 = mod.BoundedQueue(10)
    consumed = []
    c_lock = threading.Lock()
    N_PROD, N_CONS, PER = 4, 4, 250
    total = N_PROD * PER

    def producer(pid):
        for i in range(PER):
            q3.put((pid, i))

    def consumer():
        while True:
            try:
                item = q3.get(timeout=2.0)
            except TimeoutError:
                return
            with c_lock:
                consumed.append(item)
                if len(consumed) >= total:
                    return

    threads = ([threading.Thread(target=producer, args=(p,)) for p in range(N_PROD)]
               + [threading.Thread(target=consumer) for _ in range(N_CONS)])
    for t in threads: t.start()
    for t in threads: t.join(timeout=30)

    check(not any(t.is_alive() for t in threads), "stress test hung")
    check(len(consumed) == total,
          f"consumed {len(consumed)} of {total} items")
    check(len(set(consumed)) == total, "an item was delivered twice")


def test_06(mod):
    starts, ends = [], []
    lock = threading.Lock()
    in_flight = {"n": 0, "peak": 0}

    def on_start(url):
        with lock:
            starts.append(time.monotonic())
            in_flight["n"] += 1
            in_flight["peak"] = max(in_flight["peak"], in_flight["n"])

    def on_end(url):
        with lock:
            in_flight["n"] -= 1
            ends.append(time.monotonic())

    urls = [f"u{i}" for i in range(15)]
    results = mod.crawl(urls, max_concurrent=3, calls_per_second=5,
                        on_start=on_start, on_end=on_end)

    check(len(results) == 15, f"expected 15 results, got {len(results)}")
    check(in_flight["peak"] <= 3,
          f"concurrency limit broken: peak was {in_flight['peak']}, max 3")

    # Rate limit: no 1-second window may contain more than 5 starts.
    # +1 tolerance for token-bucket boundary effects.
    worst = max(sum(1 for s in starts if t <= s < t + 1.0) for t in starts)
    check(worst <= 6, f"rate limit broken: {worst} calls started in one second "
                      f"(limit 5)")


@repeat(3)
def test_07(mod):
    out = []
    lock = threading.Lock()

    def make(label):
        def fn():
            with lock:
                out.append(label)
        return fn

    mod.run_in_order(make("first"), make("second"), make("third"))
    check(out == ["first", "second", "third"], f"wrong order: {out}")

    for n in (1, 2, 9, 20):
        seq = mod.print_numbers(n)
        check(seq == list(range(1, n + 1)),
              f"print_numbers({n}) gave {seq}")


def test_08(mod):
    for n_workers, n_phases in ((4, 3), (3, 5), (6, 2)):
        aggregates, violations = mod.run_simulation(n_workers, n_phases)
        expected = [sum((w + 1) * (p + 1) for w in range(n_workers))
                    for p in range(n_phases)]
        check(aggregates == expected,
              f"aggregates {aggregates} != expected {expected}")
        check(not violations, f"ordering violations detected: {violations}")


def test_09(mod):
    random.seed(42)
    urls = [f"site{i}.com" for i in range(30)]

    t0 = time.perf_counter()
    out = mod.scrape(urls, max_workers=8, max_retries=3)
    elapsed = time.perf_counter() - t0

    check(elapsed < 30, f"scrape took {elapsed:.1f}s -- too slow / hung")
    check(set(out) >= {"ok", "failed"}, "must return keys 'ok' and 'failed'")
    check(len(out["ok"]) + len(out["failed"]) == 30,
          f"expected 30 urls accounted for, got "
          f"{len(out['ok'])} + {len(out['failed'])}")
    check(set(out["ok"]) | set(out["failed"]) == set(urls),
          "some urls missing from the result")
    # With a 30% failure rate and 3 retries, P(all 4 attempts fail) ~ 0.8%.
    check(len(out["ok"]) >= 25,
          f"only {len(out['ok'])}/30 succeeded -- are retries working?")

    # Never-succeeds path must terminate, not hang.
    def always_fails(url):
        raise mod.FetchError("permanent")

    out2 = mod.scrape(["x.com", "y.com"], max_retries=2, fetch=always_fails)
    check(len(out2["failed"]) == 2 and not out2["ok"],
          f"permanent failures mishandled: {out2}")


def test_10(mod):
    for n_items, n_parsers, n_writers in ((100, 4, 2), (50, 2, 3), (30, 1, 1)):
        t0 = time.perf_counter()
        records = mod.run_pipeline(n_items, n_parsers, n_writers, qsize=10)
        elapsed = time.perf_counter() - t0

        check(elapsed < 20, f"pipeline took {elapsed:.1f}s -- hung?")
        check(len(records) == n_items,
              f"expected {n_items} records, got {len(records)} "
              f"(items lost or duplicated)")
        ids = sorted(r["id"] for r in records)
        check(ids == list(range(n_items)), "ids are not exactly 0..n-1")
        check(all(r["value"] == r["id"] * 2 for r in records),
              "parser stage produced wrong values")


def test_11(mod):
    root = os.path.dirname(HERE)          # the multithreading/ directory
    hits = mod.search_tree(root, r"threading\.Lock\(\)")

    check(isinstance(hits, list), "search_tree must return a list")
    check(len(hits) > 5, f"expected several matches, got {len(hits)}")
    for path, lineno, line in hits:
        check(isinstance(lineno, int) and lineno > 0, f"bad line number {lineno}")
        check("threading.Lock()" in line, f"line does not contain the match: {line!r}")
        check(os.path.exists(path), f"path does not exist: {path}")

    # A pattern that matches nothing. Built by concatenation so the literal
    # never appears in this file -- check.py is itself inside the search tree,
    # and a hardcoded string would match itself.
    impossible = "qq" + "_no_such_pattern_" + "qq"
    check(mod.search_tree(root, impossible) == [],
          "should return [] when nothing matches")


def test_12(mod):
    calls = []
    lock = threading.Lock()

    def compute(key):
        with lock:
            calls.append(key)
        time.sleep(0.25)
        return f"value-{key}"

    cache = mod.SingleFlightCache(compute)

    # (1) 20 threads, same key -> compute exactly once.
    results = []
    r_lock = threading.Lock()

    def ask(key):
        v = cache.get(key)
        with r_lock:
            results.append(v)

    threads = [threading.Thread(target=ask, args=("hot",)) for _ in range(20)]
    for t in threads: t.start()
    for t in threads: t.join(timeout=20)

    check(len(calls) == 1, f"compute ran {len(calls)} times for one key, expected 1")
    check(results == ["value-hot"] * 20, "not all threads got the same value")

    # (2) 5 different keys concurrently -> must NOT serialise.
    calls.clear()
    results.clear()
    threads = [threading.Thread(target=ask, args=(f"k{i}",)) for i in range(5)]
    t0 = time.perf_counter()
    for t in threads: t.start()
    for t in threads: t.join(timeout=20)
    elapsed = time.perf_counter() - t0

    check(len(calls) == 5, f"expected 5 computes, got {len(calls)}")
    check(elapsed < 0.8,
          f"5 distinct keys took {elapsed:.2f}s -- a global lock is serialising "
          f"them (should be ~0.25s, not ~1.25s)")

    # (3) a warm key is a cache hit, no recompute.
    calls.clear()
    check(cache.get("hot") == "value-hot", "cached value lost")
    check(not calls, "recomputed an already-cached key")


def test_13(mod):
    lock = mod.ReadWriteLock()

    # Readers must genuinely overlap.
    peak = {"n": 0, "cur": 0}
    stats = threading.Lock()

    def reader(hold=0.15):
        with lock.read_lock():
            with stats:
                peak["cur"] += 1
                peak["n"] = max(peak["n"], peak["cur"])
            time.sleep(hold)
            with stats:
                peak["cur"] -= 1

    threads = [threading.Thread(target=reader) for _ in range(6)]
    for t in threads: t.start()
    for t in threads: t.join(timeout=10)
    check(peak["n"] >= 5,
          f"readers did not run concurrently (peak {peak['n']}, expected ~6)")

    # A writer must be exclusive.
    violations = []
    v_lock = threading.Lock()
    state = {"readers": 0, "writers": 0}
    s_lock = threading.Lock()

    def checked_reader():
        with lock.read_lock():
            with s_lock:
                state["readers"] += 1
                if state["writers"]:
                    with v_lock:
                        violations.append("reader ran during a write")
            time.sleep(0.01)
            with s_lock:
                state["readers"] -= 1

    def checked_writer():
        with lock.write_lock():
            with s_lock:
                state["writers"] += 1
                if state["readers"] or state["writers"] > 1:
                    with v_lock:
                        violations.append(
                            f"writer not exclusive: {dict(state)}")
            time.sleep(0.02)
            with s_lock:
                state["writers"] -= 1

    threads = ([threading.Thread(target=checked_reader) for _ in range(20)]
               + [threading.Thread(target=checked_writer) for _ in range(5)])
    random.shuffle(threads)
    for t in threads: t.start()
    for t in threads: t.join(timeout=20)
    check(not any(t.is_alive() for t in threads), "rwlock deadlocked")
    check(not violations, f"exclusion violated: {violations[:3]}")

    # No writer starvation under continuous read load.
    stop = threading.Event()
    writer_got_in = threading.Event()

    def spam_reads():
        while not stop.is_set():
            with lock.read_lock():
                time.sleep(0.005)

    def eventual_writer():
        time.sleep(0.1)
        with lock.write_lock():
            writer_got_in.set()

    readers = [threading.Thread(target=spam_reads, daemon=True) for _ in range(8)]
    for t in readers: t.start()
    w = threading.Thread(target=eventual_writer)
    w.start()

    got_in = writer_got_in.wait(timeout=5)
    stop.set()
    w.join(timeout=5)
    for t in readers: t.join(timeout=5)
    check(got_in, "WRITER STARVATION: the writer never got in under read load")


def test_14(mod):
    for name in ("dine_ordered", "dine_limited"):
        fn = getattr(mod, name, None)
        check(fn is not None, f"{name} is missing")

        t0 = time.perf_counter()
        meals = fn(5, 3)
        elapsed = time.perf_counter() - t0

        check(elapsed < 15, f"{name} took {elapsed:.1f}s -- deadlocked?")
        check(len(meals) == 5, f"{name} returned {len(meals)} entries, expected 5")
        check(all(m == 3 for m in meals),
              f"{name}: not everyone ate 3 times -> {meals}")

    # Larger table, more meals -- shakes out ordering mistakes.
    meals = mod.dine_ordered(7, 4)
    check(all(m == 4 for m in meals), f"dine_ordered(7, 4) -> {meals}")


def test_15(mod):
    # Single-threaded correctness first.
    c = mod.LRUCache(3)
    for i in range(3):
        c.put(f"k{i}", i)
    check(c.get("k0") == 0, "k0 should be present")
    c.put("k3", 3)                    # k1 is now LRU -> evicted
    check(c.get("k1") is None, "k1 should have been evicted (LRU order wrong)")
    check(c.get("k0") == 0, "k0 was used recently and must survive")
    check(c.get("k2") == 2 and c.get("k3") == 3, "k2/k3 should be present")
    check(len(c) == 3, f"len is {len(c)}, capacity is 3")

    s = c.stats
    check(s["evictions"] == 1, f"expected 1 eviction, got {s['evictions']}")
    check(s["misses"] == 1, f"expected 1 miss, got {s['misses']}")

    # Concurrent: capacity must NEVER be exceeded.
    cache = mod.LRUCache(50)
    errors = []
    e_lock = threading.Lock()

    def hammer(worker_id):
        try:
            for i in range(500):
                key = f"key-{random.randrange(200)}"
                if random.random() < 0.5:
                    cache.put(key, worker_id)
                else:
                    cache.get(key)
                if len(cache) > 50:
                    with e_lock:
                        errors.append(f"capacity exceeded: {len(cache)}")
        except Exception as exc:
            with e_lock:
                errors.append(f"{type(exc).__name__}: {exc}")

    threads = [threading.Thread(target=hammer, args=(i,)) for i in range(10)]
    for t in threads: t.start()
    for t in threads: t.join(timeout=30)

    check(not any(t.is_alive() for t in threads), "LRU cache deadlocked")
    check(not errors, f"errors under concurrency: {errors[:3]}")
    check(len(cache) <= 50, f"final size {len(cache)} exceeds capacity 50")

    # Stats must be exact.
    c2 = mod.LRUCache(10)
    for i in range(10):
        c2.put(f"k{i}", i)

    def read_all():
        for i in range(10):
            c2.get(f"k{i}")           # 10 hits each
        for i in range(10, 20):
            c2.get(f"k{i}")           # 10 misses each

    threads = [threading.Thread(target=read_all) for _ in range(10)]
    for t in threads: t.start()
    for t in threads: t.join(timeout=30)

    s = c2.stats
    check(s["hits"] == 100, f"expected 100 hits, got {s['hits']}")
    check(s["misses"] == 100, f"expected 100 misses, got {s['misses']}")


TESTS = {n: globals()[f"test_{n:02d}"] for n in range(1, 16)}

NAMES = {
    1: "Parallel sum", 2: "Ordered downloader", 3: "Thread-safe counter",
    4: "Fix the buggy bank", 5: "Bounded blocking queue", 6: "Rate-limited crawler",
    7: "Print in order", 8: "Phased simulation", 9: "Scraper with retries",
    10: "Multi-stage pipeline", 11: "Parallel file search", 12: "Single-flight cache",
    13: "Read-write lock", 14: "Dining philosophers", 15: "Thread-safe LRU cache",
}


def run_one(problem, use_solution):
    label = f"[{problem:2}] {NAMES[problem]:<26}"
    try:
        module = load(problem, use_solution)
    except FileNotFoundError as exc:
        print(f"{label} SKIP   {exc}")
        return None

    t0 = time.perf_counter()
    try:
        TESTS[problem](module)
    except NotImplementedError:
        print(f"{label} TODO   not implemented yet")
        return None
    except Failure as exc:
        print(f"{label} FAIL   {exc}")
        return False
    except Exception as exc:
        print(f"{label} ERROR  {type(exc).__name__}: {exc}")
        return False
    print(f"{label} PASS   ({time.perf_counter() - t0:.1f}s)")
    return True


def main():
    args = sys.argv[1:]
    use_solution = "--solution" in args or "-s" in args
    numbers = [int(a) for a in args if a.isdigit()] or list(range(1, 16))

    source = "reference solutions" if use_solution else "your answers"
    print(f"Checking {source} -- {len(numbers)} problem(s)")
    print("=" * 60)

    outcomes = [run_one(n, use_solution) for n in numbers]

    passed = outcomes.count(True)
    failed = outcomes.count(False)
    todo = outcomes.count(None)
    print("=" * 60)
    print(f"{passed} passed, {failed} failed, {todo} not attempted")
    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(main())
