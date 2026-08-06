"""
Module 14 - Threads vs processes vs asyncio: choosing correctly.

Run:  python multithreading/examples/14_threads_vs_processes_vs_async.py
"""

import asyncio
import multiprocessing
import os
import threading
import time
from concurrent.futures import ProcessPoolExecutor, ThreadPoolExecutor

SHARED = {"value": 0}


def mutate_shared(n):
    """Runs in a thread -> sees the real dict. In a process -> sees a COPY."""
    SHARED["value"] += n
    return SHARED["value"], os.getpid()


def demo_1_memory_model():
    print("\n--- 1. Threads SHARE memory, processes do NOT ---")
    SHARED["value"] = 0

    with ThreadPoolExecutor(max_workers=2) as pool:
        results = list(pool.map(mutate_shared, [10, 10]))
    print(f"  threads   : results={results} -> SHARED is now {SHARED['value']}")
    print(f"              same pid ({os.getpid()}), same memory")

    SHARED["value"] = 0
    with ProcessPoolExecutor(max_workers=2) as pool:
        results = list(pool.map(mutate_shared, [10, 10]))
    print(f"  processes : results={results}")
    print(f"              parent's SHARED is STILL {SHARED['value']} -- untouched")
    print("  Each process got its own copy. Different pids, separate memory.")
    print("  Cross-process data needs pickling: Queue, Pipe, Manager, shared_memory.")


def demo_2_cost():
    print("\n--- 2. Startup cost: thread vs process ---")

    def noop():
        pass

    N = 50
    t0 = time.perf_counter()
    for _ in range(N):
        t = threading.Thread(target=noop)
        t.start(); t.join()
    thread_time = (time.perf_counter() - t0) / N

    t0 = time.perf_counter()
    with ProcessPoolExecutor(max_workers=4) as pool:
        list(pool.map(int, range(N)))
    process_pool_time = time.perf_counter() - t0

    print(f"  spawn+join one thread : {thread_time * 1000:.3f} ms")
    print(f"  {N} trivial tasks through a 4-process pool: "
          f"{process_pool_time * 1000:.0f} ms total")
    print("  Threads are cheap (~microseconds). Processes cost tens of ms each")
    print("  on Windows ('spawn' re-imports your module in every child).")
    print("  -> Never create a process per small task. Use a pool.")


def demo_3_asyncio():
    print("\n--- 3. asyncio: concurrency on ONE thread, switching only at `await` ---")

    async def fetch(name, delay):
        print(f"    {name} started")
        await asyncio.sleep(delay)          # yields control HERE, explicitly
        print(f"    {name} finished")
        return name

    async def main():
        t0 = time.perf_counter()
        results = await asyncio.gather(
            fetch("A", 0.3), fetch("B", 0.2), fetch("C", 0.1),
        )
        return results, time.perf_counter() - t0

    results, elapsed = asyncio.run(main())
    print(f"  gather -> {results} in {elapsed:.2f}s (not 0.6s: they overlapped)")
    print(f"  and all of it on ONE thread: {threading.active_count()} thread(s) alive")
    print("""
  The difference that matters:
    threads  - PREEMPTIVE. A switch can happen between any two bytecodes.
               You need locks. You get races.
    asyncio  - COOPERATIVE. A switch happens ONLY at `await`. Between awaits
               your code is atomic, so most races simply cannot occur.
    The cost: one blocking call (time.sleep, requests.get, a heavy loop)
    freezes the ENTIRE event loop. Everything must be async, all the way down.""")


def demo_4_bridging():
    print("\n--- 4. Bridging: run blocking code from async ---")

    def blocking_io(n):
        time.sleep(0.2)                     # a legacy blocking library
        return n * 2

    async def main():
        t0 = time.perf_counter()
        # asyncio.to_thread runs it in a thread pool so the loop stays responsive.
        results = await asyncio.gather(*(asyncio.to_thread(blocking_io, i)
                                         for i in range(4)))
        return results, time.perf_counter() - t0

    results, elapsed = asyncio.run(main())
    print(f"  asyncio.to_thread x4 -> {results} in {elapsed:.2f}s (not 0.8s)")
    print("  Use asyncio.to_thread() for blocking I/O,")
    print("  and loop.run_in_executor(ProcessPoolExecutor(), fn) for CPU-bound work.")


def demo_5_decision_table():
    print("\n--- 5. The decision table ---")
    print(f"""
  +-------------------+-------------+---------------+------------------+
  |                   | Threads     | Processes     | asyncio          |
  +-------------------+-------------+---------------+------------------+
  | memory            | shared      | separate      | shared           |
  | parallel CPU      | NO (GIL)    | YES           | NO               |
  | good for          | I/O-bound   | CPU-bound     | massive I/O      |
  | cost per unit     | ~8 MB stack | ~10s of MB    | ~KBs             |
  | practical scale   | hundreds    | ~{os.cpu_count():<2} (cores)   | 10,000s          |
  | switching         | preemptive  | preemptive    | cooperative      |
  | needs locks       | YES         | no (isolated) | rarely           |
  | main danger       | races,      | pickling,     | one blocking     |
  |                   | deadlocks   | startup cost  | call stalls all  |
  | blocking libs OK  | YES         | YES           | NO               |
  +-------------------+-------------+---------------+------------------+

  DECIDE LIKE THIS:
    1. Is it CPU-bound?                     -> ProcessPoolExecutor
    2. I/O-bound + blocking libraries?      -> ThreadPoolExecutor   (most common)
    3. I/O-bound + async libs + 1000s conns -> asyncio
    4. Not sure?                            -> ThreadPoolExecutor, then measure

  WINDOWS / macOS spawn notes (you are on {os.name}):
    - multiprocessing uses 'spawn': children RE-IMPORT your module.
    - `if __name__ == "__main__":` is MANDATORY or you fork-bomb yourself.
    - target functions must be top-level (picklable) -- no lambdas, no closures.
    - start method here: {multiprocessing.get_start_method()}""")


if __name__ == "__main__":          # <- mandatory for the process demos
    demo_1_memory_model()
    demo_2_cost()
    demo_3_asyncio()
    demo_4_bridging()
    demo_5_decision_table()
