"""
Problem 11 - Parallel file search.  (Tier 3, Modules 12-13)

Search a directory tree for lines matching a regex, using a thread pool.

Requirements:
  - return [(path, line_number, line_text), ...]
  - a file that can't be read (binary, permissions) must NOT kill a worker
  - bounded: don't submit 100,000 futures at once

Thinking point: is this I/O-bound or CPU-bound? Does a complex regex change
the answer? (Module 13.)

Check:  python multithreading/exercises/check.py 11
"""

import os
import re
from concurrent.futures import ThreadPoolExecutor, as_completed


def search_tree(root, pattern, max_workers=8, batch_size=200):
    """Return a list of (path, line_number, line) for every match under `root`."""
    # TODO
    #   Hints:
    #     - walk the tree with os.walk, collect paths (cheap, single-threaded)
    #     - submit ONE task per file; each task opens the file and scans lines
    #     - wrap the whole per-file body in try/except OSError/UnicodeDecodeError
    #       -> return [] for unreadable files instead of raising
    #     - use errors="ignore" when opening, or you'll blow up on binaries
    #     - to bound memory, submit in batches of `batch_size` rather than
    #       building one giant list of futures
    #     - compile the regex ONCE, outside the workers
    raise NotImplementedError


if __name__ == "__main__":
    here = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    hits = search_tree(here, r"threading\.Lock")
    for path, lineno, line in hits[:10]:
        print(f"{os.path.basename(path)}:{lineno}: {line.strip()[:60]}")
    print(f"... {len(hits)} matches total")
