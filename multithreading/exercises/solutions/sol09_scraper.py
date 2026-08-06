"""Solution 9 - Web scraper with retries."""

import random
import time
from concurrent.futures import ThreadPoolExecutor, as_completed


class FetchError(Exception):
    pass


def unreliable_fetch(url, failure_rate=0.3):
    time.sleep(0.02)
    if random.random() < failure_rate:
        raise FetchError(f"transient failure for {url}")
    return f"content-of-{url}"


def scrape(urls, max_workers=8, max_retries=3, fetch=unreliable_fetch,
           base_delay=0.01):

    def fetch_with_retry(url):
        """Retry INSIDE the worker, so the pool sees one task per url."""
        last_error = None
        for attempt in range(max_retries + 1):
            try:
                return fetch(url)
            except Exception as exc:
                last_error = exc
                if attempt == max_retries:
                    break
                # Exponential backoff + JITTER. Without the jitter every
                # failing task retries at the same instants and stampedes the
                # server in synchronised waves.
                delay = base_delay * (2 ** attempt) + random.uniform(0, base_delay)
                time.sleep(delay)
        raise last_error

    ok, failed = {}, {}

    with ThreadPoolExecutor(max_workers=max_workers) as pool:
        # {future: url} -- the standard way to remember what a future was for.
        futures = {pool.submit(fetch_with_retry, url): url for url in urls}

        # as_completed yields in COMPLETION order, so you can stream progress
        # instead of waiting for the slowest url.
        for future in as_completed(futures):
            url = futures[future]
            try:
                ok[url] = future.result()      # exception re-raised HERE
            except Exception as exc:
                failed[url] = str(exc)

    return {"ok": ok, "failed": failed}


# WHY IT CANNOT HANG:
#   - `with ThreadPoolExecutor(...)` calls shutdown(wait=True) on exit, so
#     every worker is joined.
#   - as_completed with no timeout still terminates, because every future
#     eventually settles: fetch_with_retry either returns or raises after a
#     BOUNDED number of attempts with BOUNDED sleeps.
#   - Every future's result() is consulted inside try/except, so no exception
#     is left unretrieved (an unretrieved exception is silently swallowed).
#
# THE SUBTLE BUG TO AVOID:
#   Retrying by RE-SUBMITTING to the same pool from inside a pool worker can
#   deadlock when max_workers is small: your worker blocks waiting on a task
#   that can't be scheduled because your worker is holding the only slot.
#   Retry in-place inside the worker, as above.
