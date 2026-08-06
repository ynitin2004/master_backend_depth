"""
Problem 2 - Ordered downloader.  (Tier 1, Modules 1-3)

Fetch every url concurrently (one thread each) but return the results in the
SAME ORDER as the input list.

Rules:
  - raw threads only, no concurrent.futures
  - fetch() sleeps a random amount, so completion order != input order

Check:  python multithreading/exercises/check.py 2
"""

import random
import threading
import time


def fetch(url):
    """Given. Pretend network call -- deliberately unpredictable latency."""
    time.sleep(random.uniform(0.01, 0.15))
    return f"content-of-{url}"


def fetch_all(urls):
    """Return [fetch(u) for u in urls], computed concurrently, order preserved."""
    # TODO: your code here.
    #
    # Hints:
    #   - "which thread produced which result" is the whole problem
    #   - approach A: results = [None] * len(urls); thread i writes results[i]
    #   - approach B: push (index, value) tuples onto a queue.Queue, then sort
    #   - one of these needs no lock. Which, and why?
    raise NotImplementedError


if __name__ == "__main__":
    urls = [f"site{i}.com" for i in range(8)]
    t0 = time.perf_counter()
    out = fetch_all(urls)
    print(f"{time.perf_counter() - t0:.2f}s (sequential would be ~0.6s)")
    print(out)
