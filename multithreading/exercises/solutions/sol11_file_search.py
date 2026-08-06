"""Solution 11 - Parallel file search."""

import os
import re
from concurrent.futures import ThreadPoolExecutor, as_completed


def search_tree(root, pattern, max_workers=8, batch_size=200,
                extensions=None):
    regex = re.compile(pattern)          # compile ONCE, share across workers
                                         # (compiled patterns are thread-safe)

    def collect_paths():
        for dirpath, dirnames, filenames in os.walk(root):
            # Skip the usual noise; also stops us walking into .git
            dirnames[:] = [d for d in dirnames
                           if d not in {".git", "__pycache__", ".venv", "node_modules"}]
            for name in filenames:
                if extensions and not name.endswith(tuple(extensions)):
                    continue
                yield os.path.join(dirpath, name)

    def search_file(path):
        """Runs in a worker. MUST NOT raise -- a raising worker task turns into
        an exception at result() time and, if unchecked, kills the whole run."""
        matches = []
        try:
            with open(path, "r", encoding="utf-8", errors="ignore") as fh:
                for lineno, line in enumerate(fh, start=1):
                    if regex.search(line):
                        matches.append((path, lineno, line.rstrip("\n")))
        except (OSError, UnicodeDecodeError):
            return []                    # unreadable/binary -> skip quietly
        return matches

    results = []
    paths = list(collect_paths())

    with ThreadPoolExecutor(max_workers=max_workers) as pool:
        # Submit in BATCHES rather than all at once. With 100k files, one
        # giant list of futures pins every pending task's arguments in memory.
        for start in range(0, len(paths), batch_size):
            batch = paths[start:start + batch_size]
            futures = [pool.submit(search_file, p) for p in batch]
            for future in as_completed(futures):
                results.extend(future.result())

    return results


# IS THIS I/O-BOUND OR CPU-BOUND?
#
#   Mostly I/O-bound: open() and read() release the GIL, so threads genuinely
#   overlap and you get real speedup. Threads are the right tool.
#
#   BUT the regex matching is CPU work that holds the GIL. With a cheap pattern
#   the I/O dominates and threads win. With an expensive pattern (backtracking,
#   many alternations) over cached files, the regex dominates, the GIL
#   serialises it, and threads stop helping -- that's when you switch to
#   ProcessPoolExecutor.
#
#   The honest answer in an interview: "it depends on the ratio, and I'd
#   measure it" -- then describe the benchmark (Module 13).
#
#   Caveat on SSD vs spinning disk: on an HDD, heavy parallel reads cause seek
#   thrashing and MORE threads can be slower. On NVMe, more is generally better.
