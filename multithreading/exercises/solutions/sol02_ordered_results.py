"""Solution 2 - Ordered downloader."""

import queue
import random
import threading
import time


def fetch(url):
    time.sleep(random.uniform(0.01, 0.15))
    return f"content-of-{url}"


def fetch_all(urls, fetch=fetch):
    """Approach A: pre-sized list. Each thread owns one index -> NO LOCK."""
    results = [None] * len(urls)

    def worker(index, url):
        results[index] = fetch(url)      # exclusive slot, no contention

    threads = [threading.Thread(target=worker, args=(i, u))
               for i, u in enumerate(urls)]
    for t in threads: t.start()
    for t in threads: t.join()
    return results


def fetch_all_queue(urls, fetch=fetch):
    """Approach B: queue of (index, value), sorted at the end.

    Queue is internally locked, so this is safe too -- just more work.
    Use this shape when you don't know the result count up front.
    """
    out = queue.Queue()

    def worker(index, url):
        out.put((index, fetch(url)))

    threads = [threading.Thread(target=worker, args=(i, u))
               for i, u in enumerate(urls)]
    for t in threads: t.start()
    for t in threads: t.join()

    collected = [out.get() for _ in range(len(urls))]
    return [value for _, value in sorted(collected)]


# WHY APPROACH A NEEDS NO LOCK:
#   A data race requires two threads touching the SAME memory. Here each
#   thread writes results[i] for its own unique i, so there is no shared
#   mutable location. (The list object itself is shared, but list slot
#   assignment is a single atomic store and the indices never collide.)
#
#   results.append(...) would be different -- then every thread hits the same
#   end-of-list, and you'd also lose the ordering.
