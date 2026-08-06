"""
Problem 6 - Rate-limited crawler.  (Tier 2, Modules 6, 12)

Implement crawl() with TWO independent limits enforced simultaneously:
  - at most `max_concurrent` requests in flight at any instant
  - at most `calls_per_second` requests STARTED in any 1-second window

Check:  python multithreading/exercises/check.py 6
"""

import threading
import time


def crawl(urls, max_concurrent=3, calls_per_second=5, on_start=None, on_end=None):
    """Fetch every url, honouring both limits. Return a list of results.

    on_start(url) / on_end(url) are optional callbacks the CHECKER uses to
    record timestamps. Call on_start(url) immediately before the request and
    on_end(url) immediately after -- but only if they are not None.
    """
    # TODO: your code here.
    #
    # Hints:
    #   - "at most N at once"        -> threading.Semaphore(N)
    #   - "at most N per second"     -> a token bucket guarded by a Lock
    #   - the two are SEPARATE limits; you need both, not one or the other
    #   - CRITICAL: never time.sleep() while holding the rate-limiter's lock.
    #     Compute how long to sleep inside the lock, release it, THEN sleep.
    raise NotImplementedError


def _fake_request(url):
    """Given. Stands in for the network."""
    time.sleep(0.1)
    return f"content-of-{url}"


if __name__ == "__main__":
    urls = [f"u{i}" for i in range(12)]
    t0 = time.perf_counter()
    results = crawl(urls, max_concurrent=3, calls_per_second=5)
    print(f"{len(results)} results in {time.perf_counter() - t0:.2f}s")
    print("12 urls at 5/sec -> should take at least ~1.4s")
