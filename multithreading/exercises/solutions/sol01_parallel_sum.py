"""Solution 1 - Parallel sum."""

import threading


def parallel_sum(numbers, n_threads=4):
    if not numbers:
        return 0
    n_threads = max(1, min(n_threads, len(numbers)))

    # Split into n_threads roughly equal chunks.
    size = (len(numbers) + n_threads - 1) // n_threads
    chunks = [numbers[i:i + size] for i in range(0, len(numbers), size)]

    # Pre-sized results list: each thread owns EXACTLY ONE index, so no two
    # threads ever touch the same slot -> no lock needed at all.
    partials = [0] * len(chunks)

    def work(index, chunk):
        partials[index] = sum(chunk)

    threads = [threading.Thread(target=work, args=(i, c))
               for i, c in enumerate(chunks)]
    for t in threads:       # start ALL of them...
        t.start()
    for t in threads:       # ...THEN join all of them.
        t.join()

    return sum(partials)


# ---------------------------------------------------------------------------
# Alternative with a shared accumulator. Needs a lock, and is slower because
# every thread contends on it. Shown for contrast.
def parallel_sum_with_lock(numbers, n_threads=4):
    total = 0
    lock = threading.Lock()
    size = (len(numbers) + n_threads - 1) // n_threads or 1

    def work(chunk):
        nonlocal total
        partial = sum(chunk)      # compute OUTSIDE the lock
        with lock:
            total += partial      # only the mutation is inside

    threads = [threading.Thread(target=work, args=(numbers[i:i + size],))
               for i in range(0, len(numbers), size)]
    for t in threads: t.start()
    for t in threads: t.join()
    return total


# ---------------------------------------------------------------------------
# WHY THIS IS NOT FASTER THAN sum(numbers):
#   Summing integers is CPU-BOUND pure-Python work, so the GIL serialises it
#   (Module 13). You pay thread creation + slicing costs for zero parallelism.
#   The correct tool for real CPU-bound work is ProcessPoolExecutor.
#   This exercise is about CORRECTNESS mechanics, not speed.
