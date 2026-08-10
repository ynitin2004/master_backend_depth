"""
Verify a machine coding solution against the problem's contract.

    python machine_coding/problems/check.py 1                  # your answer
    python machine_coding/problems/check.py 1 --path ~/p1      # from elsewhere
    python machine_coding/problems/check.py 1 --solution       # the reference
    python machine_coding/problems/check.py --solution         # all references

With --path, point at a directory containing `solution.py`, or at a .py file
directly. Without it, the checker looks for `pN_*.py` next to this file.

P0 failures are hard failures. P1 features you did not build are reported as
SKIP, not FAIL -- not finishing P1 is expected and fine.
"""

import argparse
import glob
import importlib.util
import os
import sys
import threading
import time

HERE = os.path.dirname(os.path.abspath(__file__))
SOLUTIONS = os.path.join(HERE, "solutions")

NAMES = {
    1: "Rate Limiter",
    2: "Pub/Sub Broker",
    3: "Connection Pool",
    4: "KV Store with TTL",
    5: "Parking Lot",
    6: "Web Crawler",
}


# --------------------------------------------------------------- infrastructure
class Failure(AssertionError):
    """A P0 requirement is broken."""


class Skipped(Exception):
    """An optional (P1) feature is not implemented."""


def check(condition, message):
    if not condition:
        raise Failure(message)


def need(obj, *names):
    """Return the named attributes, or raise Skipped if any is missing."""
    missing = [n for n in names if not hasattr(obj, n)]
    if missing:
        raise Skipped(f"not implemented: {', '.join(missing)}")
    values = [getattr(obj, n) for n in names]
    return values[0] if len(values) == 1 else values


def load(problem, use_solution, path=None):
    if path:
        target = path if path.endswith(".py") else os.path.join(path, "solution.py")
        if not os.path.exists(target):
            raise FileNotFoundError(f"no solution at {target}")
    else:
        directory = SOLUTIONS if use_solution else HERE
        matches = sorted(glob.glob(os.path.join(directory, f"p{problem}_*.py")))
        if not matches:
            raise FileNotFoundError(
                f"no p{problem}_*.py in {directory} "
                f"(write your solution there, or pass --path)")
        target = matches[0]

    spec = importlib.util.spec_from_file_location(f"mc_p{problem}", target)
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


def run_threads(fn, n, timeout=20):
    """Run fn(i) on n threads, join them, assert none hung."""
    threads = [threading.Thread(target=fn, args=(i,)) for i in range(n)]
    for t in threads:
        t.start()
    for t in threads:
        t.join(timeout=timeout)
    check(not any(t.is_alive() for t in threads),
          "threads did not finish -- deadlock or a missing timeout")


# ============================================================== 1. RATE LIMITER
def test_1(m):
    done = []

    # ---- P0: token bucket
    TokenBucket = m.TokenBucketLimiter
    bucket = TokenBucket(capacity=5, refill_rate=5, per=1.0)
    allowed = [bucket.allow("u1") for _ in range(8)]
    check(allowed[:5] == [True] * 5, f"first 5 should be allowed, got {allowed}")
    check(allowed[5:] == [False] * 3, f"6th onward should be denied, got {allowed}")
    check(bucket.allow("u2") is True, "per-key isolation broken: u2 blocked by u1")
    time.sleep(0.45)
    check(bucket.allow("u1") is True, "tokens did not refill over time")
    done.append("token bucket")

    # ---- P0: fixed window
    fixed = m.FixedWindowLimiter(limit=3, window=0.4)
    check([fixed.allow("k") for _ in range(5)] == [True, True, True, False, False],
          "fixed window did not cap at the limit")
    check(fixed.allow("other") is True, "fixed window: per-key isolation broken")
    time.sleep(0.45)
    check(fixed.allow("k") is True, "fixed window did not reset after the window")
    done.append("fixed window")

    # ---- P0: thread safety. Refill is negligible over the test, so the number
    #      of granted requests must be EXACTLY the capacity.
    strict = TokenBucket(capacity=50, refill_rate=0.001, per=1.0)
    granted, lock = [], threading.Lock()

    def hammer(_i):
        local = sum(1 for _ in range(20) if strict.allow("shared"))
        with lock:
            granted.append(local)

    run_threads(hammer, 20)
    total = sum(granted)
    check(total == 50,
          f"token bucket raced: {total} requests allowed, capacity was 50")
    done.append("thread safety")

    # ---- P1: sliding window log
    try:
        Sliding = need(m, "SlidingWindowLogLimiter")
        sliding = Sliding(limit=3, window=0.4)
        check([sliding.allow("k") for _ in range(5)] == [True] * 3 + [False] * 2,
              "sliding window did not cap at the limit")
        time.sleep(0.45)
        check([sliding.allow("k") for _ in range(3)] == [True] * 3,
              "sliding window did not free up after the window elapsed")

        # No boundary burst -- unlike a fixed window, two half-windows must not
        # combine into 2x the limit.
        tight = Sliding(limit=4, window=0.6)
        for _ in range(4):
            tight.allow("b")
        time.sleep(0.35)
        check(tight.allow("b") is False,
              "sliding window allowed a boundary burst -- that is fixed-window "
              "behaviour")
        done.append("sliding window (P1)")
    except Skipped as exc:
        done.append(f"sliding window SKIP ({exc})")

    # ---- P1: service
    try:
        Service = need(m, "RateLimiterService")
        service = Service(lambda: TokenBucket(capacity=2, refill_rate=0.001))
        check([service.allow("a") for _ in range(3)] == [True, True, False],
              "service did not apply the limiter")
        check(service.allow("b") is True, "service: per-key isolation broken")

        stats = service.stats()
        check(stats["keys"] == 2, f"expected 2 keys, got {stats}")
        check(stats["allowed"] == 3 and stats["denied"] == 1, f"stats wrong: {stats}")

        errors = []

        def spam(i):
            try:
                for j in range(50):
                    service.allow(f"key-{i}-{j % 5}")
            except Exception as exc:                       # noqa: BLE001
                errors.append(exc)

        run_threads(spam, 10)
        check(not errors, f"service raced under concurrency: {errors[:2]}")
        done.append("service (P1)")
    except Skipped as exc:
        done.append(f"service SKIP ({exc})")

    # ---- P1: eviction
    try:
        Service = need(m, "RateLimiterService")
        service = Service(lambda: TokenBucket(capacity=5, refill_rate=5))
        need(service, "evict_idle")
        service.allow("old")
        time.sleep(0.2)
        service.allow("new")
        check(service.evict_idle(older_than=0.1) >= 1, "evict_idle removed nothing")
        check(service.stats()["keys"] < 2, "evict_idle did not free key state")
        done.append("eviction (P1)")
    except Skipped as exc:
        done.append(f"eviction SKIP ({exc})")

    return done


# ================================================================= 2. BROKER
def test_2(m):
    done = []
    Broker = m.Broker

    broker = Broker()
    try:
        broker.create_topic("orders")

        # A subscriber sees only messages published AFTER it subscribed.
        broker.publish("orders", {"n": -1})
        broker.subscribe("orders", "sub-a")
        broker.subscribe("orders", "sub-b")
        for i in range(5):
            broker.publish("orders", {"n": i})

        batch = broker.poll("orders", "sub-a", max_messages=10)
        check([msg.payload["n"] for msg in batch] == [0, 1, 2, 3, 4],
              f"sub-a got the wrong messages: {[b.payload for b in batch]}")
        done.append("publish/subscribe/poll")

        # poll() must not advance the cursor on its own.
        check(len(broker.poll("orders", "sub-a", max_messages=10)) == 5,
              "poll advanced the cursor without an ack")
        broker.ack("orders", "sub-a", batch[-1].offset)
        check(broker.poll("orders", "sub-a") == [], "ack did not advance the cursor")
        done.append("ack semantics")

        # Independent cursors: sub-b is untouched by sub-a's progress.
        check(len(broker.poll("orders", "sub-b", max_messages=10)) == 5,
              "cursors are not independent -- sub-b lost messages")
        done.append("independent cursors")

        # Offsets unique and nothing lost under concurrent publishers.
        broker.create_topic("bulk")
        broker.subscribe("bulk", "reader")
        offsets, lock = [], threading.Lock()

        def publisher(i):
            local = [broker.publish("bulk", {"w": i, "j": j}) for j in range(50)]
            with lock:
                offsets.extend(local)

        run_threads(publisher, 10)
        check(len(offsets) == 500, f"lost publishes: {len(offsets)}")
        check(len(set(offsets)) == 500,
              f"duplicate offsets -> the log raced ({len(set(offsets))} unique)")

        seen = 0
        while True:
            batch = broker.poll("bulk", "reader", max_messages=100)
            if not batch:
                break
            seen += len(batch)
            broker.ack("bulk", "reader", batch[-1].offset)
        check(seen == 500, f"reader saw {seen} of 500 messages")
        done.append("concurrent publishing")
    finally:
        broker.shutdown()

    # ---- P1: push delivery
    broker = Broker()
    try:
        need(broker, "subscribe_callback")
        broker.create_topic("push")
        received, recv_lock = [], threading.Lock()

        def good(msg):
            with recv_lock:
                received.append(msg.payload)

        def bad(msg):
            raise RuntimeError("subscriber blew up")

        broker.subscribe_callback("push", "good", good)
        broker.subscribe_callback("push", "bad", bad)
        for i in range(5):
            broker.publish("push", i)

        deadline = time.monotonic() + 5
        while len(received) < 5 and time.monotonic() < deadline:
            time.sleep(0.02)
        check(sorted(received) == [0, 1, 2, 3, 4],
              f"push delivery lost messages: {received}")
        done.append("push delivery (P1)")

        # The raising subscriber must not have killed the delivery threads.
        broker.publish("push", 99)
        deadline = time.monotonic() + 5
        while 99 not in received and time.monotonic() < deadline:
            time.sleep(0.02)
        check(99 in received, "a raising subscriber killed delivery for everyone")
        done.append("subscriber isolation (P1)")
    except Skipped as exc:
        done.append(f"push delivery SKIP ({exc})")
    finally:
        broker.shutdown()

    # ---- P1: retention
    broker = Broker()
    try:
        broker.create_topic("capped", max_messages=3)
        broker.subscribe("capped", "r")
        for i in range(10):
            broker.publish("capped", i)
        batch = broker.poll("capped", "r", max_messages=100)
        check(len(batch) <= 3,
              f"retention not applied: {len(batch)} retained, cap was 3")
        check([b.payload for b in batch] == [7, 8, 9],
              f"retention dropped the wrong end: {[b.payload for b in batch]}")
        done.append("retention (P1)")
    except (Skipped, TypeError) as exc:
        done.append(f"retention SKIP ({exc})")
    finally:
        broker.shutdown()

    return done


# ======================================================== 3. CONNECTION POOL
def test_3(m):
    done = []
    Pool = m.ConnectionPool
    TimeoutErr = getattr(m, "PoolTimeoutError", Exception)

    created, created_lock = [], threading.Lock()

    def factory():
        with created_lock:
            created.append(1)
        time.sleep(0.01)
        return {"id": len(created), "open": True, "valid": True}

    # ---- P0: reuse, timeout, blocking handoff
    created.clear()
    pool = Pool(factory, max_size=3, timeout=1.0)
    try:
        conn = pool.acquire()
        pool.release(conn)
        again = pool.acquire()
        check(len(created) == 1, f"pool did not reuse: created {len(created)}")
        pool.release(again)
        done.append("reuse")

        held = [pool.acquire() for _ in range(3)]
        check(len(created) == 3, f"created {len(created)}, expected 3")
        t0 = time.monotonic()
        try:
            pool.acquire(timeout=0.2)
            raise Failure("acquire() on an exhausted pool should have raised")
        except TimeoutErr:
            elapsed = time.monotonic() - t0
            check(0.15 <= elapsed <= 1.5,
                  f"timeout honoured badly: waited {elapsed:.2f}s for 0.2s")
        for conn in held:
            pool.release(conn)
        done.append("timeout")

        # A blocked acquirer must be woken by a release.
        blocker = [pool.acquire() for _ in range(3)]
        got = []

        def waiter(_i):
            conn = pool.acquire(timeout=5)
            got.append(conn)
            pool.release(conn)

        thread = threading.Thread(target=waiter, args=(0,))
        thread.start()
        time.sleep(0.1)
        check(not got, "acquire() did not block on an exhausted pool")
        pool.release(blocker[0])
        thread.join(timeout=5)
        check(len(got) == 1, "a blocked acquirer was never woken by release()")
        for conn in blocker[1:]:
            pool.release(conn)
        done.append("blocking handoff")
    finally:
        pool.close()

    # ---- P0: THE test. max_size must hold under concurrency.
    created.clear()
    pool = Pool(factory, max_size=5, timeout=10.0)
    try:
        peak = {"n": 0, "cur": 0}
        peak_lock = threading.Lock()
        errors = []

        def worker(_i):
            try:
                for _ in range(10):
                    conn = pool.acquire(timeout=10)
                    with peak_lock:
                        peak["cur"] += 1
                        peak["n"] = max(peak["n"], peak["cur"])
                    time.sleep(0.005)
                    with peak_lock:
                        peak["cur"] -= 1
                    pool.release(conn)
            except Exception as exc:                       # noqa: BLE001
                errors.append(exc)

        run_threads(worker, 20, timeout=60)
        check(not errors, f"errors under concurrency: {errors[:2]}")
        check(len(created) <= 5,
              f"POOL EXCEEDED max_size: created {len(created)}, max was 5")
        check(peak["n"] <= 5,
              f"{peak['n']} connections were checked out at once, max was 5")
        check(pool.stats()["in_use"] == 0, f"connections leaked: {pool.stats()}")
        done.append("max_size under concurrency")
    finally:
        pool.close()

    # ---- P0: context manager releases on exception
    created.clear()
    pool = Pool(factory, max_size=1, timeout=1.0)
    try:
        try:
            with pool.connection():
                raise ValueError("boom")
        except ValueError:
            pass
        conn = pool.acquire(timeout=0.5)      # would hang if it was not released
        pool.release(conn)
        done.append("context manager")
    finally:
        pool.close()

    # ---- P1: min_size prewarm
    created.clear()
    try:
        pool = Pool(factory, min_size=2, max_size=4)
        check(len(created) == 2,
              f"min_size did not prewarm: {len(created)} created, expected 2")
        pool.close()
        done.append("min_size (P1)")
    except (TypeError, Failure) as exc:
        done.append(f"min_size SKIP ({exc})")

    # ---- P1: validator
    created.clear()
    try:
        pool = Pool(factory, max_size=2, timeout=1.0, validator=lambda c: c["valid"])
        conn = pool.acquire()
        conn["valid"] = False                 # poison it
        pool.release(conn)
        fresh = pool.acquire(timeout=1.0)
        check(fresh["valid"] is True, "validator returned an invalid connection")
        check(len(created) == 2, "validator did not replace the bad connection")
        pool.release(fresh)
        pool.close()
        done.append("validator (P1)")
    except (TypeError, Failure) as exc:
        done.append(f"validator SKIP ({exc})")

    # ---- P1: close rejects further acquires
    try:
        pool = Pool(factory, max_size=2)
        pool.close()
        try:
            pool.acquire(timeout=0.2)
            done.append("close-rejects SKIP (acquire succeeded after close)")
        except Exception:
            done.append("close rejects (P1)")
    except Exception as exc:                               # noqa: BLE001
        done.append(f"close SKIP ({exc})")

    return done


# ============================================================== 4. KV STORE
def test_4(m):
    done = []
    store = m.KVStore(sweep_interval=0.1)
    try:
        # ---- P0: basics
        store.set("a", 1)
        check(store.get("a") == 1, "get did not return what set stored")
        check(store.get("missing") is None, "a missing key should return None")
        check(store.exists("a") is True and store.exists("missing") is False,
              "exists() is wrong")
        check(store.delete("a") is True and store.get("a") is None,
              "delete did not remove the key")
        check(store.delete("a") is False, "deleting a missing key should be False")
        done.append("basic crud")

        # ---- P0: expiry is immediate, not sweep-dependent
        store.set("temp", "v", ttl=0.2)
        check(store.get("temp") == "v", "value gone before its ttl")
        time.sleep(0.25)
        check(store.get("temp") is None, "AN EXPIRED KEY WAS RETURNED")
        check("temp" not in store.keys(), "expired key still in keys()")
        check(store.exists("temp") is False, "expired key still 'exists'")
        done.append("lazy expiry")

        # ---- P0: thread safety
        errors = []

        def churn(i):
            try:
                for j in range(200):
                    store.set(f"k-{i}-{j % 10}", j, ttl=1)
                    store.get(f"k-{i}-{j % 10}")
            except Exception as exc:                       # noqa: BLE001
                errors.append(exc)

        run_threads(churn, 10)
        check(not errors, f"errors under concurrency: {errors[:2]}")
        done.append("thread safety")

        # ---- P1: nx
        try:
            check(store.set("nx", 1, nx=True) is True, "nx on a new key should store")
            check(store.set("nx", 2, nx=True) is False,
                  "nx on an existing key should refuse")
            check(store.get("nx") == 1, "nx overwrote the existing value")
            done.append("nx (P1)")
        except TypeError as exc:
            done.append(f"nx SKIP ({exc})")

        # ---- P1: atomic incr
        try:
            need(store, "incr")
            store.delete("counter")

            def bump(_i):
                for _ in range(500):
                    store.incr("counter")

            run_threads(bump, 10)
            check(store.get("counter") == 5000,
                  f"incr raced: got {store.get('counter')}, expected 5000")
            done.append("atomic incr (P1)")
        except Skipped as exc:
            done.append(f"incr SKIP ({exc})")

        # ---- P1: single-flight get_or_set
        try:
            need(store, "get_or_set")
            calls, calls_lock = [], threading.Lock()

            def slow():
                with calls_lock:
                    calls.append(1)
                time.sleep(0.25)
                return "computed"

            values, values_lock = [], threading.Lock()

            def ask(_i):
                value = store.get_or_set("hot", slow)
                with values_lock:
                    values.append(value)

            run_threads(ask, 20)
            check(len(calls) == 1,
                  f"CACHE STAMPEDE: the factory ran {len(calls)} times, expected 1")
            check(values == ["computed"] * 20, "not all callers got the value")
            done.append("single flight (P1)")

            # Distinct keys must not serialise behind one global lock.
            calls.clear()
            t0 = time.monotonic()

            def ask_distinct(i):
                store.get_or_set(f"key-{i}", slow)

            run_threads(ask_distinct, 5)
            elapsed = time.monotonic() - t0
            check(len(calls) == 5, f"expected 5 computes, got {len(calls)}")
            check(elapsed < 0.8,
                  f"5 distinct keys took {elapsed:.2f}s -- a global lock is "
                  f"serialising them (should be ~0.25s)")
            done.append("per-key locking (P1)")
        except Skipped as exc:
            done.append(f"get_or_set SKIP ({exc})")

        # ---- P1: the active sweep actually reclaims memory
        try:
            need(store, "stats")
            for i in range(200):
                store.set(f"sweep-{i}", i, ttl=0.1)
            before = store.stats().get("tracked", store.size())
            time.sleep(0.6)
            after = store.stats().get("tracked", store.size())
            check(after < before - 100,
                  f"the sweeper did not reclaim memory: {before} -> {after} "
                  f"(lazy expiry alone leaks keys nobody reads)")
            done.append("active sweep (P1)")
        except Skipped as exc:
            done.append(f"sweep SKIP ({exc})")
    finally:
        store.close()

    return done


# =========================================================== 5. PARKING LOT
def test_5(m):
    done = []
    SpotSize, Vehicle, ParkingLot = m.SpotSize, m.Vehicle, m.ParkingLot
    LotFull = getattr(m, "LotFullError", Exception)

    # ---- P0: park / unpark / availability
    lot = ParkingLot(layout={0: {SpotSize.SMALL: 1, SpotSize.MEDIUM: 2}})
    avail = lot.availability()
    check(avail[SpotSize.SMALL] == 1 and avail[SpotSize.MEDIUM] == 2,
          f"initial availability wrong: {avail}")

    ticket = lot.park(Vehicle("KA-1", SpotSize.SMALL))
    check(ticket.spot_id is not None, "park() returned no spot")
    check(lot.availability()[SpotSize.SMALL] == 0, "availability did not decrease")

    receipt = lot.unpark(ticket.id)
    check(receipt.fee >= 0, "receipt has no fee")
    check(lot.availability()[SpotSize.SMALL] == 1, "the spot was not freed")
    done.append("park/unpark")

    # ---- P0: a vehicle fits its own size or larger
    lot = ParkingLot(layout={0: {SpotSize.SMALL: 1, SpotSize.LARGE: 1}})
    lot.park(Vehicle("A", SpotSize.SMALL))               # takes the small
    check(lot.park(Vehicle("B", SpotSize.SMALL)) is not None,
          "a small vehicle could not fall back to a larger spot")
    try:
        lot.park(Vehicle("C", SpotSize.LARGE))
        raise Failure("parking in a full lot should have raised LotFullError")
    except LotFull:
        pass
    done.append("size fitting + LotFullError")

    # ---- P0: THE test. No spot may ever be double-assigned.
    lot = ParkingLot(layout={0: {SpotSize.MEDIUM: 10}})
    tickets, rejected = [], []
    lock = threading.Lock()

    def try_park(i):
        try:
            ticket = lot.park(Vehicle(f"CAR-{i}", SpotSize.MEDIUM))
            with lock:
                tickets.append(ticket)
        except LotFull:
            with lock:
                rejected.append(i)

    run_threads(try_park, 40)
    spots = [t.spot_id for t in tickets]
    check(len(tickets) == 10,
          f"{len(tickets)} cars parked into 10 spots (expected exactly 10)")
    check(len(set(spots)) == len(spots),
          f"SPOT DOUBLE-ASSIGNED: {len(spots)} tickets, {len(set(spots))} spots")
    check(len(rejected) == 30, f"expected 30 rejections, got {len(rejected)}")
    done.append("no double allocation")

    # ---- P0: concurrent park/unpark churn keeps the books balanced
    lot = ParkingLot(layout={0: {SpotSize.MEDIUM: 5}})
    errors = []

    def churn(i):
        try:
            for _ in range(20):
                try:
                    ticket = lot.park(Vehicle(f"V-{i}", SpotSize.MEDIUM))
                except LotFull:
                    continue
                lot.unpark(ticket.id)
        except Exception as exc:                           # noqa: BLE001
            errors.append(exc)

    run_threads(churn, 10, timeout=30)
    check(not errors, f"errors under churn: {errors[:2]}")
    check(lot.availability()[SpotSize.MEDIUM] == 5,
          f"spots leaked: {lot.availability()} (expected all 5 free)")
    done.append("park/unpark churn")

    # ---- P1: pricing strategies
    try:
        Hourly, Flat = need(m, "HourlyPricing", "FlatRatePricing")
        flat_lot = ParkingLot(layout={0: {SpotSize.SMALL: 1}}, pricing=Flat(rate=99.0))
        ticket = flat_lot.park(Vehicle("F-1", SpotSize.SMALL))
        check(flat_lot.unpark(ticket.id).fee == 99.0,
              "FlatRatePricing was not applied")

        hourly = Hourly()
        cheap = hourly.compute(SpotSize.SMALL, 3600)
        check(hourly.compute(SpotSize.LARGE, 3600) > cheap,
              "larger spots should not be cheaper")
        check(hourly.compute(SpotSize.SMALL, 3601) > cheap,
              "part-hours should round up")
        done.append("pricing strategies (P1)")
    except Skipped as exc:
        done.append(f"pricing SKIP ({exc})")

    # ---- P1: multiple floors
    try:
        lot = ParkingLot(layout={0: {SpotSize.MEDIUM: 1}, 1: {SpotSize.MEDIUM: 1}})
        first = lot.park(Vehicle("M-1", SpotSize.MEDIUM))
        second = lot.park(Vehicle("M-2", SpotSize.MEDIUM))
        check({first.floor, second.floor} == {0, 1}, "the second floor was never used")
        check(first.floor == 0, "allocation should prefer the lowest floor")
        done.append("multi-floor (P1)")
    except (Failure, AttributeError, KeyError) as exc:
        done.append(f"multi-floor SKIP ({exc})")

    # ---- P1: find_vehicle + duplicate rejection
    try:
        need(ParkingLot, "find_vehicle")
        lot = ParkingLot(layout={0: {SpotSize.MEDIUM: 2}})
        ticket = lot.park(Vehicle("FIND-ME", SpotSize.MEDIUM))
        check(lot.find_vehicle("FIND-ME") == ticket.spot_id,
              "find_vehicle returned the wrong spot")
        check(lot.find_vehicle("NOT-HERE") is None,
              "find_vehicle should return None for an absent plate")
        try:
            lot.park(Vehicle("FIND-ME", SpotSize.MEDIUM))
            done.append("find_vehicle (P1, no duplicate check)")
        except Exception:
            done.append("find_vehicle + duplicate rejection (P1)")
    except Skipped as exc:
        done.append(f"find_vehicle SKIP ({exc})")

    return done


# ============================================================== 6. CRAWLER
def test_6(m):
    done = []
    Crawler = m.Crawler

    WEB = {
        "http://a/":  ["http://a/1", "http://a/2", "http://b/"],
        "http://a/1": ["http://a/3", "http://a/"],       # cycle
        "http://a/2": ["http://a/3"],                    # diamond
        "http://a/3": ["http://a/1"],                    # cycle
        "http://b/":  ["http://b/1", "http://a/"],
        "http://b/1": [],
    }

    def make_fetcher(log, log_lock, fail=()):
        def fetcher(url):
            with log_lock:
                log.append(url)
            time.sleep(0.01)
            if url in fail:
                raise ConnectionError(f"cannot reach {url}")
            return f"content:{url}", WEB.get(url, [])
        return fetcher

    # ---- P0: each URL fetched at most once, and it terminates
    log, lock = [], threading.Lock()
    crawler = Crawler(make_fetcher(log, lock), n_workers=4, max_depth=3, max_pages=50)
    t0 = time.monotonic()
    result = crawler.crawl(["http://a/"])
    elapsed = time.monotonic() - t0

    check(elapsed < 20, f"the crawl took {elapsed:.1f}s -- did it terminate?")
    check(len(log) == len(set(log)),
          f"A URL WAS FETCHED TWICE: {len(log)} fetches, {len(set(log))} unique")
    check(set(result.pages) == set(WEB),
          f"missed pages: {set(WEB) - set(result.pages)}")
    check(result.fetched == 6, f"fetched {result.fetched}, expected 6")
    done.append("dedup + termination")

    # ---- P0: depth limiting
    log, lock = [], threading.Lock()
    shallow = Crawler(make_fetcher(log, lock), n_workers=4, max_depth=1, max_pages=50)
    result = shallow.crawl(["http://a/"])
    check(max(result.depth_of.values()) <= 1,
          f"depth limit broken: reached depth {max(result.depth_of.values())}")
    check(set(result.pages) == {"http://a/", "http://a/1", "http://a/2", "http://b/"},
          f"the depth-1 crawl fetched the wrong set: {sorted(result.pages)}")
    done.append("depth limit")

    # ---- P0: page cap
    log, lock = [], threading.Lock()
    capped = Crawler(make_fetcher(log, lock), n_workers=4, max_depth=5, max_pages=3)
    result = capped.crawl(["http://a/"])
    check(result.fetched <= 3,
          f"max_pages broken: fetched {result.fetched}, cap was 3")
    done.append("page cap")

    # ---- P0: a failing fetch is recorded, not fatal
    log, lock = [], threading.Lock()
    crawler = Crawler(make_fetcher(log, lock, fail={"http://a/2"}),
                      n_workers=4, max_depth=3, max_pages=50)
    t0 = time.monotonic()
    result = crawler.crawl(["http://a/"])
    check(time.monotonic() - t0 < 20, "a failing fetch hung the crawl")
    check("http://a/2" in result.errors,
          f"the failure was not recorded: {result.errors}")
    check(len(result.pages) >= 4,
          f"one failure aborted the crawl: only {len(result.pages)} pages")
    done.append("error isolation")

    # ---- P0: heavy fan-out, still exactly-once, still terminates
    big = {f"http://x/{i}": [f"http://x/{j}" for j in range(30)] for i in range(30)}
    log, lock = [], threading.Lock()

    def big_fetcher(url):
        with lock:
            log.append(url)
        return "c", big.get(url, [])

    crawler = Crawler(big_fetcher, n_workers=8, max_depth=3, max_pages=100)
    t0 = time.monotonic()
    result = crawler.crawl([f"http://x/{i}" for i in range(5)])
    check(time.monotonic() - t0 < 30, "the heavy fan-out crawl did not terminate")
    check(len(log) == len(set(log)),
          f"fan-out raced: {len(log)} fetches, {len(set(log))} unique")
    check(result.fetched <= 100, f"exceeded max_pages: {result.fetched}")
    done.append("fan-out exactly-once")

    # ---- P1: retries
    try:
        attempts, att_lock = {}, threading.Lock()

        def flaky(url):
            with att_lock:
                attempts[url] = attempts.get(url, 0) + 1
                n = attempts[url]
            if url == "http://a/1" and n < 3:
                raise ConnectionError("transient")
            return "c", WEB.get(url, [])

        crawler = Crawler(flaky, n_workers=4, max_depth=2, max_pages=50, max_retries=3)
        result = crawler.crawl(["http://a/"])
        check("http://a/1" in result.pages,
              f"retries did not recover the flaky page: {result.errors}")
        check(attempts["http://a/1"] == 3,
              f"expected 3 attempts, got {attempts.get('http://a/1')}")
        done.append("retries (P1)")
    except TypeError as exc:
        done.append(f"retries SKIP ({exc})")

    # ---- P1: on_page callback
    try:
        seen, seen_lock = [], threading.Lock()

        def on_page(url, content, depth):
            with seen_lock:
                seen.append(url)

        log, lock = [], threading.Lock()
        crawler = Crawler(make_fetcher(log, lock), n_workers=4, max_depth=2,
                          max_pages=50, on_page=on_page)
        result = crawler.crawl(["http://a/"])
        check(len(seen) == result.fetched,
              f"on_page fired {len(seen)} times for {result.fetched} pages")
        done.append("on_page callback (P1)")
    except TypeError as exc:
        done.append(f"on_page SKIP ({exc})")

    return done


TESTS = {n: globals()[f"test_{n}"] for n in range(1, 7)}


# ------------------------------------------------------------------- runner
def run_one(problem, use_solution, path=None):
    label = f"[{problem}] {NAMES[problem]:<20}"
    try:
        module = load(problem, use_solution, path)
    except FileNotFoundError as exc:
        print(f"{label} SKIP   {exc}")
        return None
    except Exception as exc:                                # noqa: BLE001
        print(f"{label} ERROR  import failed: {type(exc).__name__}: {exc}")
        return False

    t0 = time.perf_counter()
    try:
        details = TESTS[problem](module)
    except NotImplementedError:
        print(f"{label} TODO   not implemented yet")
        return None
    except Failure as exc:
        print(f"{label} FAIL   {exc}")
        return False
    except AttributeError as exc:
        print(f"{label} FAIL   missing from the required API: {exc}")
        return False
    except Exception as exc:                                # noqa: BLE001
        print(f"{label} ERROR  {type(exc).__name__}: {exc}")
        return False

    print(f"{label} PASS   ({time.perf_counter() - t0:.1f}s)")
    for line in details:
        print(f"       {'-' if 'SKIP' in line else '+'} {line}")
    return True


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("problems", nargs="*", type=int, help="problem numbers 1-6")
    parser.add_argument("--solution", "-s", action="store_true",
                        help="run the reference solutions")
    parser.add_argument("--path", "-p", help="directory or .py file to test")
    args = parser.parse_args()

    numbers = args.problems or list(range(1, 7))
    for n in numbers:
        if n not in TESTS:
            parser.error(f"no problem {n} (valid: 1-6)")

    source = "reference solutions" if args.solution else (args.path or "your answers")
    print(f"Checking {source} -- {len(numbers)} problem(s)")
    print("=" * 64)

    outcomes = [run_one(n, args.solution, args.path) for n in numbers]

    print("=" * 64)
    print(f"{outcomes.count(True)} passed, {outcomes.count(False)} failed, "
          f"{outcomes.count(None)} not attempted")
    return 1 if outcomes.count(False) else 0


if __name__ == "__main__":
    sys.exit(main())
