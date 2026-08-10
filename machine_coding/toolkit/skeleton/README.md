# The Skeleton

The structure you type at **minute 10**, without thinking, for any problem.

It runs as-is. Copy the folder, rename `service/` to your domain, replace `Entity` with your
noun, and start filling in `core.py`.

```bash
cp -r machine_coding/toolkit/skeleton ~/practice/my_problem
cd ~/practice/my_problem
python demo.py
python -m unittest test_service.py -v
```

## The typing order (memorise this, not the code)

| # | File | Time | Why this order |
|---|---|---|---|
| 1 | `NOTES.md` | 2 min | Tiers first. Converts a scary vague problem into a checklist. |
| 2 | `exceptions.py` | 30 sec | Trivial to write, immediately signals thoroughness. |
| 3 | `models.py` | 4 min | **The highest-leverage file.** Naming the domain makes the rest fall out. |
| 4 | `store.py` | 3 min | Shared state + the lock, created in the same minute. |
| 5 | `core.py` | 3 min | Public API as stubs. Signatures only, no bodies yet. |
| 6 | `demo.py` | 2 min | Import it all, call the stubs, **RUN IT.** |

At minute 20 you have a running program. Everything after that makes it better instead of
hoping it comes together at the end.

## Why each file exists

**`exceptions.py`** — Custom exception types. Six lines, and it's a visible signal you think
about error paths. `raise ValueError` everywhere reads as sloppy.

**`models.py`** — Dataclasses and enums, **no logic**. Writing this first forces you to name
your entities, which is where the design actually comes from. Enums instead of magic
strings is free credit.

**`store.py`** — Owns the shared state *and* the lock. Nothing else in the codebase locks.
One owner per piece of state is the rule that keeps concurrency tractable under time
pressure.

**`core.py`** — The service/orchestration layer. Talks to the store, applies rules, exposes
the public API. This is where your business logic lives.

**`demo.py`** — Your UI. The interviewer runs this. Make it print clearly, in sections, so
your features are *visible* rather than merely present.

**`test_service.py`** — Happy path, edge case, error case, concurrency, shutdown.

## Adapting it

- **Needs background workers?** (scheduler, broker, pipeline) — add `workers.py`, import
  `WorkerPool` from [`../primitives.py`](../primitives.py).
- **Problem says "different strategies/policies/algorithms"?** — add `strategies.py` with an
  ABC and **two** implementations. That's the design credit, in full.
- **No background threads at all?** (cache, rate limiter, parking lot) — delete
  `WorkerPool`; the lock in `store.py` is your entire concurrency story, and that's fine.

## The drill

Set a 20-minute timer. Build only the skeleton — models, exceptions, stubs, running
`demo.py` — for a problem from [`../../problems/`](../../problems/). No real logic.

Do that five times, on five different problems.

After five reps the blank page stops being blank. That is the specific fear, and this is the
specific cure.
