"""Solution 6 - Rate-limited crawler."""

import threading
import time
from concurrent.futures import ThreadPoolExecutor


class TokenBucket:
    """At most `rate` acquisitions per `per` seconds, across all threads.

    `initial` is the starting token count = the size of the allowed BURST.

    A classic token bucket starts FULL (initial=rate), which permits a burst of
    `rate` calls at t=0 followed by `rate` more refilled over the next second
    -- i.e. up to 2*rate in a single sliding 1-second window. That is the
    intended, documented behaviour of a token bucket.

    If the requirement is the STRICTER "no more than `rate` in ANY 1-second
    window", start with initial=1. Then calls are spaced `per/rate` apart and
    no sliding window can ever contain more than `rate` of them.
    """

    def __init__(self, rate, per=1.0, initial=None):
        self._rate = float(rate)
        self._per = float(per)
        self._tokens = float(rate if initial is None else initial)
        self._last = time.monotonic()
        self._lock = threading.Lock()

    def acquire(self):
        while True:
            with self._lock:
                now = time.monotonic()
                # Refill in proportion to elapsed time, capped at the bucket size.
                self._tokens = min(
                    self._rate,
                    self._tokens + (now - self._last) * self._rate / self._per,
                )
                self._last = now
                if self._tokens >= 1:
                    self._tokens -= 1
                    return
                # Work out how long until one token is available.
                wait = (1 - self._tokens) * self._per / self._rate
            # SLEEP OUTSIDE THE LOCK. Sleeping while holding it would block
            # every other thread from even checking, serialising everything.
            time.sleep(wait)


def _fake_request(url):
    time.sleep(0.1)
    return f"content-of-{url}"


def crawl(urls, max_concurrent=3, calls_per_second=5,
          on_start=None, on_end=None, request=_fake_request):
    # TWO SEPARATE LIMITS, both enforced:
    #   semaphore -> how many are IN FLIGHT at one instant
    #   bucket    -> how many are STARTED per second
    # They are independent. Fast requests need the bucket; slow ones need the
    # semaphore. A real crawler needs both.
    semaphore = threading.Semaphore(max_concurrent)
    # initial=1, not initial=calls_per_second: the spec says "at most N started
    # in ANY 1-second window", and a full bucket would allow 2N across the
    # window that straddles the initial burst. See TokenBucket's docstring.
    bucket = TokenBucket(calls_per_second, per=1.0, initial=1)

    def fetch_one(url):
        bucket.acquire()                 # rate limit first (cheap to wait on)
        with semaphore:                  # then take a concurrency slot
            if on_start:
                on_start(url)
            try:
                return request(url)
            finally:
                if on_end:
                    on_end(url)          # in `finally`: an exception must
                                         # still record the end, or the
                                         # concurrency count drifts

    # max_workers must be >= max_concurrent or the pool becomes the real limit.
    with ThreadPoolExecutor(max_workers=max(max_concurrent, 8)) as pool:
        return list(pool.map(fetch_one, urls))


# WHY THE ORDER (bucket then semaphore) MATTERS:
#   Taking the semaphore first would mean threads sit on a concurrency slot
#   while waiting out the rate limit -- the slot is occupied but no work is
#   happening. Rate-limit first, then occupy a slot only when you're about to
#   actually issue the request.
