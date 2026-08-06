"""
Module 13 - The GIL, measured on YOUR machine.

Run:  python multithreading/examples/13_gil_benchmark.py
(takes ~30-60s -- it is doing real work)

Do not memorise the conclusion. Read the numbers.
"""

import os
import sys
import threading
import time
from concurrent.futures import ProcessPoolExecutor, ThreadPoolExecutor

CPU_WORK = 6_000_000        # iterations of pure-Python arithmetic
IO_DELAY = 0.25             # simulated network latency, seconds


def cpu_task(n=CPU_WORK):
    """Pure Python arithmetic: holds the GIL the entire time."""
    total = 0
    for i in range(n):
        total += i * i
    return total


def io_task(delay=IO_DELAY):
    """time.sleep RELEASES the GIL -- stands in for a network/DB/disk call."""
    time.sleep(delay)
    return "ok"


def timed(fn, *args):
    t0 = time.perf_counter()
    fn(*args)
    return time.perf_counter() - t0


# --------------------------------------------------------------------------
def bench_cpu_threads():
    print("\n" + "=" * 68)
    print("TEST 1 - CPU-BOUND work with THREADS")
    print("=" * 68)

    base = timed(lambda: [cpu_task() for _ in range(4)])
    print(f"  4 tasks, sequential (1 thread) : {base:6.2f}s   <- baseline")

    def run_threaded(n):
        ts = [threading.Thread(target=cpu_task) for _ in range(n)]
        for t in ts: t.start()
        for t in ts: t.join()

    for n in (2, 4):
        el = timed(run_threaded, n)
        print(f"  {n} tasks in {n} threads          : {el:6.2f}s"
              f"   ({(base * n / 4) / el:.2f}x vs doing them one at a time)")

    print("""
  VERDICT: ~1.0x. No speedup, sometimes WORSE.
  Only one thread can execute Python bytecode at a time (the GIL), so the
  work is just time-sliced across threads instead of being split up.
  The extra time is switching overhead.""")


def bench_cpu_processes():
    print("\n" + "=" * 68)
    print("TEST 2 - the SAME CPU-bound work with PROCESSES")
    print("=" * 68)

    n = 4
    seq = timed(lambda: [cpu_task() for _ in range(n)])
    print(f"  {n} tasks, sequential            : {seq:6.2f}s")

    t0 = time.perf_counter()
    with ProcessPoolExecutor(max_workers=n) as pool:
        list(pool.map(cpu_task, [CPU_WORK] * n))
    par = time.perf_counter() - t0

    print(f"  {n} tasks, {n} processes           : {par:6.2f}s   "
          f"({seq / par:.2f}x speedup)")
    print(f"""
  VERDICT: real parallelism. Each process has its OWN interpreter and its
  OWN GIL, so all {n} cores work at once (you have {os.cpu_count()} logical cores).
  Cost: process startup, and arguments/results must be picklable and copied.""")


def bench_io_threads():
    print("\n" + "=" * 68)
    print("TEST 3 - I/O-BOUND work with THREADS")
    print("=" * 68)

    n_tasks = 16
    seq = timed(lambda: [io_task() for _ in range(n_tasks)])
    print(f"  {n_tasks} tasks, sequential           : {seq:6.2f}s   <- baseline")

    for workers in (2, 4, 8, 16):
        t0 = time.perf_counter()
        with ThreadPoolExecutor(max_workers=workers) as pool:
            list(pool.map(lambda _: io_task(), range(n_tasks)))
        el = time.perf_counter() - t0
        print(f"  {n_tasks} tasks, {workers:2} threads          : {el:6.2f}s   "
              f"({seq / el:5.2f}x speedup)")

    print("""
  VERDICT: near-LINEAR speedup. This is what threads are for.
  A sleeping/waiting thread RELEASES the GIL, so the others run. Same for
  socket reads, DB queries, file I/O, and most C extensions (numpy, zlib...).""")


def bench_switch_interval():
    print("\n" + "=" * 68)
    print("TEST 4 - sys.setswitchinterval: how often threads rotate")
    print("=" * 68)

    print(f"  default switch interval: {sys.getswitchinterval()}s (5ms)")
    original = sys.getswitchinterval()

    def four_cpu_threads():
        ts = [threading.Thread(target=cpu_task, args=(CPU_WORK // 2,))
              for _ in range(4)]
        for t in ts: t.start()
        for t in ts: t.join()

    for interval in (0.005, 0.000_01):
        sys.setswitchinterval(interval)
        el = timed(four_cpu_threads)
        print(f"  interval={interval:<10} 4 CPU threads: {el:.2f}s")

    sys.setswitchinterval(original)
    print("""
  A shorter interval = more context switches = more overhead, but each thread
  waits less to get a turn. Lowering it to a microsecond is a great way to
  EXPOSE race conditions in tests (Module 16); it is a bad idea in production.""")


def summary():
    gil = getattr(sys, "_is_gil_enabled", lambda: True)()
    print("\n" + "=" * 68)
    print("SUMMARY")
    print("=" * 68)
    print(f"""
  Python {sys.version.split()[0]}, {os.cpu_count()} logical cores, GIL enabled: {gil}

  +----------------+------------------+--------------------------------+
  | Workload       | Threads          | Processes                      |
  +----------------+------------------+--------------------------------+
  | CPU-bound      | no gain (GIL)    | ~Nx gain  <-- use this         |
  | I/O-bound      | big gain <-- use | works, but wasteful overhead   |
  +----------------+------------------+--------------------------------+

  How to tell which you have: if the code is WAITING (network, disk, DB,
  sleep, subprocess), it is I/O-bound -> threads. If it is BURNING CPU
  (loops, math, parsing, compression in pure Python), it is CPU-bound
  -> processes.

  Escape hatches for CPU-bound work without processes:
    - numpy / pandas / lxml / zlib release the GIL inside their C code
    - Cython / C extensions can release it explicitly
    - free-threaded builds (3.13+) remove the GIL entirely (experimental)""")


if __name__ == "__main__":
    # REQUIRED on Windows: child processes re-import this module, and without
    # this guard they would re-run the benchmarks -> infinite process explosion.
    print(f"Python {sys.version.split()[0]} | {os.cpu_count()} logical cores")
    print("This takes ~30-60s of real work. Numbers vary by machine and load.")

    bench_cpu_threads()
    bench_cpu_processes()
    bench_io_threads()
    bench_switch_interval()
    summary()
