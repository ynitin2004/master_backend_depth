"""Problem 6 - Concurrent Web Crawler. Reference solution.

The interesting part is TERMINATION DETECTION, not the fetching.
"""

import queue
import threading
import time
from dataclasses import dataclass, field
from typing import Callable, Optional
from urllib.parse import urlparse


@dataclass
class CrawlResult:
    pages: dict = field(default_factory=dict)      # url -> content
    errors: dict = field(default_factory=dict)     # url -> error string
    depth_of: dict = field(default_factory=dict)   # url -> depth
    fetched: int = 0
    skipped: int = 0
    duration_seconds: float = 0.0


class _DomainLimiter:
    """Politeness: max concurrent requests AND max rate, per domain."""

    def __init__(self, max_concurrent: int = 2, rate_per_second: Optional[float] = None):
        self._max_concurrent = max_concurrent
        self._rate = rate_per_second
        self._semaphores: dict[str, threading.Semaphore] = {}
        self._last_call: dict[str, float] = {}
        self._lock = threading.Lock()

    def _semaphore_for(self, domain: str) -> threading.Semaphore:
        with self._lock:
            sem = self._semaphores.get(domain)
            if sem is None:
                sem = threading.Semaphore(self._max_concurrent)
                self._semaphores[domain] = sem
            return sem

    def acquire(self, url: str) -> threading.Semaphore:
        domain = urlparse(url).netloc or url
        sem = self._semaphore_for(domain)
        sem.acquire()

        if self._rate is not None:
            min_gap = 1.0 / self._rate
            while True:
                with self._lock:
                    last = self._last_call.get(domain, 0.0)
                    now = time.monotonic()
                    if now - last >= min_gap:
                        self._last_call[domain] = now
                        break
                    wait = min_gap - (now - last)
                time.sleep(wait)          # OUTSIDE the lock, always
        return sem


class Crawler:
    def __init__(self, fetcher: Callable[[str], tuple], n_workers: int = 4,
                 max_depth: int = 2, max_pages: int = 100, max_retries: int = 0,
                 rate_per_second: Optional[float] = None,
                 max_per_domain: int = 4,
                 on_page: Optional[Callable[[str, str, int], None]] = None):
        self._fetcher = fetcher
        self._n_workers = n_workers
        self._max_depth = max_depth
        self._max_pages = max_pages
        self._max_retries = max_retries
        self._on_page = on_page
        self._limiter = _DomainLimiter(max_per_domain, rate_per_second)

        self._frontier: queue.Queue = queue.Queue()
        self._seen: set[str] = set()
        self._result = CrawlResult()
        self._lock = threading.Lock()
        self._stop = threading.Event()

    # ---------------------------------------------------------------- API
    def crawl(self, seed_urls: list[str]) -> CrawlResult:
        started = time.monotonic()
        self._result = CrawlResult()
        self._seen = set()
        self._stop.clear()

        for url in seed_urls:
            self._enqueue(url, depth=0)

        workers = [threading.Thread(target=self._worker, name=f"crawler-{i}",
                                    daemon=True)
                   for i in range(self._n_workers)]
        for worker in workers:
            worker.start()

        # ================= TERMINATION DETECTION =================
        # NOT "wait until the queue is empty" -- a worker can be mid-fetch,
        # about to enqueue ten more URLs.
        #
        # Queue.join() blocks until every put() has a matching task_done().
        # The unfinished-task counter therefore covers items that are
        # DEQUEUED BUT NOT YET COMPLETE, which is exactly the gap that naive
        # "is the queue empty" checks miss.
        #
        # The invariant that makes it work: a worker enqueues its children
        # BEFORE calling task_done() on the parent, so the counter never
        # transiently hits zero while work remains.
        self._frontier.join()
        # =========================================================

        self._stop.set()
        for worker in workers:
            worker.join(timeout=5)

        self._result.duration_seconds = time.monotonic() - started
        return self._result

    def stop(self) -> None:
        """Cancel from another thread. Cooperative -- workers check the flag."""
        self._stop.set()

    # ------------------------------------------------------------ workers
    def _worker(self) -> None:
        while True:
            try:
                url, depth = self._frontier.get(timeout=0.1)
            except queue.Empty:
                if self._stop.is_set():
                    return
                continue

            try:
                if not self._stop.is_set():
                    self._process(url, depth)
            except Exception as exc:                      # noqa: BLE001
                # A worker that lets an exception escape DIES, the pool
                # shrinks silently, and frontier.join() may hang forever.
                with self._lock:
                    self._result.errors[url] = f"{type(exc).__name__}: {exc}"
            finally:
                # ALWAYS in finally. A missed task_done() means join() never
                # returns and crawl() hangs.
                self._frontier.task_done()

    def _process(self, url: str, depth: int) -> None:
        content, links = self._fetch_with_retry(url)

        with self._lock:
            self._result.pages[url] = content
            self._result.depth_of[url] = depth
            self._result.fetched += 1

        # Children enqueued BEFORE this task's task_done() (which happens in
        # the worker's finally). That ordering is what makes join() correct.
        if depth < self._max_depth:
            for link in links:
                self._enqueue(link, depth + 1)

        if self._on_page is not None:
            try:
                self._on_page(url, content, depth)   # outside the lock
            except Exception:
                pass

    def _fetch_with_retry(self, url: str) -> tuple:
        last_error = None
        for attempt in range(self._max_retries + 1):
            sem = self._limiter.acquire(url)
            try:
                return self._fetcher(url)
            except Exception as exc:                      # noqa: BLE001
                last_error = exc
                if attempt < self._max_retries:
                    time.sleep(0.01 * (2 ** attempt))
            finally:
                sem.release()
        raise last_error

    # ----------------------------------------------------------- frontier
    def _enqueue(self, url: str, depth: int) -> None:
        with self._lock:
            # Dedup is a CHECK-THEN-ACT: `if url not in seen: seen.add(url)`
            # must be one atomic step, or two workers both fetch the same URL.
            if url in self._seen:
                self._result.skipped += 1
                return
            if len(self._seen) >= self._max_pages:
                self._result.skipped += 1
                return
            if depth > self._max_depth:
                self._result.skipped += 1
                return
            self._seen.add(url)
        self._frontier.put((url, depth))


# ===========================================================================
if __name__ == "__main__":
    # A small fake web with cycles and a dead link.
    WEB = {
        "http://a.com/":      ["http://a.com/1", "http://a.com/2", "http://b.com/"],
        "http://a.com/1":     ["http://a.com/3", "http://a.com/"],       # cycle
        "http://a.com/2":     ["http://a.com/3"],                        # diamond
        "http://a.com/3":     ["http://a.com/1"],                        # cycle
        "http://b.com/":      ["http://b.com/1", "http://a.com/"],
        "http://b.com/1":     [],
    }
    fetch_log = []
    log_lock = threading.Lock()

    def fetcher(url):
        with log_lock:
            fetch_log.append(url)
        time.sleep(0.02)
        if url == "http://broken.com/":
            raise ConnectionError("host unreachable")
        return f"<html>{url}</html>", WEB.get(url, [])

    crawler = Crawler(fetcher, n_workers=4, max_depth=3, max_pages=50)
    result = crawler.crawl(["http://a.com/", "http://broken.com/"])

    print(f"fetched     : {result.fetched}")
    print(f"errors      : {result.errors}")
    print(f"skipped     : {result.skipped} (duplicates + depth/page limits)")
    print(f"duration    : {result.duration_seconds:.2f}s")
    print(f"pages       : {sorted(result.pages)}")
    print(f"depths      : {dict(sorted(result.depth_of.items()))}")

    print(f"\nfetch calls : {len(fetch_log)}")
    print(f"unique urls : {len(set(fetch_log))}")
    print(f"each url fetched at most once: {len(fetch_log) == len(set(fetch_log))}")

    print("\n--- depth limiting ---")
    shallow = Crawler(fetcher, n_workers=4, max_depth=1, max_pages=50)
    result = shallow.crawl(["http://a.com/"])
    print(f"max_depth=1 -> {result.fetched} pages, depths "
          f"{sorted(set(result.depth_of.values()))}")

    print("\n--- page cap ---")
    capped = Crawler(fetcher, n_workers=4, max_depth=5, max_pages=3)
    result = capped.crawl(["http://a.com/"])
    print(f"max_pages=3 -> {result.fetched} pages fetched")
