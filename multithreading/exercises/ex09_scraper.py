"""
Problem 9 - Web scraper with retries.  (Tier 3, Module 12)

Fetch every url with a ThreadPoolExecutor. ~30% of fetches fail randomly.

Requirements:
  - retry each failure up to `max_retries` times, exponential backoff + jitter
  - return {"ok": {url: content}, "failed": {url: last_error_message}}
  - consume results with as_completed (react as they land, not in one batch)
  - must never hang, even if every url fails permanently

Check:  python multithreading/exercises/check.py 9
"""

import random
import time
from concurrent.futures import ThreadPoolExecutor, as_completed


class FetchError(Exception):
    pass


def unreliable_fetch(url, failure_rate=0.3):
    """Given. Fails `failure_rate` of the time."""
    time.sleep(0.02)
    if random.random() < failure_rate:
        raise FetchError(f"transient failure for {url}")
    return f"content-of-{url}"


def scrape(urls, max_workers=8, max_retries=3, fetch=unreliable_fetch):
    """Return {"ok": {...}, "failed": {...}}."""
    # TODO
    #   Hints:
    #     - write a helper `fetch_with_retry(url)` that loops max_retries times
    #       and re-raises on the final attempt. Submit THAT to the pool, so the
    #       retry happens inside the worker.
    #     - backoff: delay = base * 2**attempt + random.uniform(0, base)
    #       The jitter matters: without it every failing task retries in
    #       lockstep and hammers the server in synchronised waves.
    #     - {future: url} dict so as_completed can tell you which url it was
    #     - wrap fut.result() in try/except -- that is where the error surfaces
    raise NotImplementedError


if __name__ == "__main__":
    random.seed(0)
    urls = [f"site{i}.com" for i in range(30)]
    t0 = time.perf_counter()
    out = scrape(urls)
    print(f"{len(out['ok'])} ok, {len(out['failed'])} failed "
          f"in {time.perf_counter() - t0:.2f}s")
