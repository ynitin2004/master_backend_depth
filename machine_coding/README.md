# The Machine Coding Round — Playbook

You are not scared of concurrency. You already know concurrency. You are scared of the
**format**: a blank editor, a vague problem, a running clock, and no idea whether you're
ahead or behind.

That is a process problem, and process problems are fixable by drilling. This document is
the process.

---

## Part 1 — What this round actually is

**The format.** You get a loosely-specified problem ("design an in-memory rate limiter",
"build a job scheduler"), 90–120 minutes, your own machine and IDE. You produce **working,
running code**. Then 15–30 minutes of the interviewer poking at it: "how would you add X?",
"what happens if two threads do Y?"

**What it is NOT:**

- Not LeetCode. There's no clever algorithm. The hard part is *structure*, not insight.
- Not system design. No Kafka, no Redis, no load balancers. **Everything is in-memory, one
  process.** If you catch yourself drawing boxes, stop.
- Not a completeness contest. Nobody finishes every requirement. That's deliberate.

**The single thing that gets people rejected:** code that doesn't run at the end. A
half-scoped solution that runs and has two tests beats a beautiful three-quarters-finished
design that throws `ImportError` when the interviewer types `python main.py`.

### How you're actually scored

Roughly in this order of weight:

| Weight | Criterion | What it means concretely |
|---|---|---|
| ★★★★★ | **It runs** | `python demo.py` works. Tests pass. No commented-out code. |
| ★★★★ | **Core requirements work** | The P0 features are demonstrably functional. |
| ★★★★ | **Correct concurrency** | Shared state is guarded. No obvious race. You can explain your locks. |
| ★★★ | **Design / extensibility** | Interfaces where the problem hints at variation. Small classes. Clear names. |
| ★★★ | **Tests** | Even 4–5 real tests. Their absence is a red flag; their presence is a strong signal. |
| ★★ | **Edge cases & errors** | Custom exceptions, validation, sane behaviour on bad input. |
| ★ | **Extra features** | Nice, but never at the cost of anything above. |

Read that table again. **"It runs" outranks everything.** Every rule below follows from it.

---

## Part 2 — The rules you must not break

1. **In-memory only.** No database, no Redis, no files unless asked, no network. Standard
   library only unless they say otherwise.
2. **No frameworks.** No Flask, no FastAPI, no Django. A `main.py` / `demo.py` that
   exercises the system *is* your UI.
3. **One process.** Threads, not microservices.
4. **Working over complete.** Cut scope, never quality.
5. **Commit / save often.** If your machine dies at minute 85 you want something on disk.
6. **Run your code every 10 minutes.** Not at the end. Every ten minutes.

That last one is the single highest-value habit in this document. An import error found at
minute 20 costs 30 seconds. The same error found at minute 88 costs you the round.

---

## Part 3 — The 90-minute clock

Print this. Internalise it. The times are the point — being "ahead" or "behind" is
knowable, and that knowledge is what kills the panic.

```
 0:00 - 0:10   CLARIFY & SCOPE      talk, don't type
 0:10 - 0:20   SKELETON             files, classes, method stubs, demo.py that RUNS
 0:20 - 0:55   P0 CORE              make the main flow actually work
 0:55 - 1:10   CONCURRENCY & TESTS  locks audited, 4-6 tests written and passing
 1:10 - 1:20   P1 FEATURES          one or two, only if P0 is solid
 1:20 - 1:30   POLISH & DEMO        README, run everything, prepare your walkthrough
```

**Milestones — check yourself against these:**

- **At 0:20** — `python demo.py` runs and prints something, even if every method is a stub.
- **At 0:55** — the happy path works end to end. If it doesn't, **stop adding features and
  cut scope now.**
- **At 1:10** — tests pass. From here you only add things you can finish in 10 minutes.
- **At 1:25** — you stop writing code. Full stop. You run everything and prepare to talk.

If you're 120 minutes, scale each block by 1.33. If you're 60 minutes, drop P1 entirely and
write 3 tests instead of 6.

---

## Part 4 — Minutes 0–10: clarify and scope

**Do not type yet.** Ten minutes of thinking here saves forty later.

### Ask these questions (pick the relevant 4–5)

- "Is this in-memory and single-process, or should I assume persistence?" *(Always ask.
  Always. It signals you know the difference.)*
- "How many concurrent users/threads should this handle?"
- "Should this be thread-safe? Are calls coming from multiple threads?" *(Almost always
  yes — and asking makes your locking look deliberate rather than lucky.)*
- "What's the read/write ratio?" *(Justifies your locking strategy later.)*
- "Should I prioritise breadth of features or depth on the core?" *(The answer is always
  depth. Making them say it out loud protects you.)*
- "Is a CLI/demo script enough, or do you want a REST API?" *(It's always the demo script.)*

### Then write the scope down, in a file

Create `NOTES.md` and type your tiers. This takes 90 seconds and it is the single best
anti-panic tool you have, because it converts "vague scary problem" into a checklist.

```markdown
## P0 - must work (target 0:55)
- [ ] register a task with a priority
- [ ] worker pool executes tasks concurrently
- [ ] get task status

## P1 - if time (target 1:20)
- [ ] retries with backoff
- [ ] delayed / scheduled execution

## P2 - mention, don't build
- persistence, cron expressions, distributed workers, metrics export

## Assumptions
- in-memory, single process
- thread-safe: calls arrive from many threads
- tasks are idempotent
```

**Say out loud:** *"I'm going to build P0 first and make sure it's solid and tested, then
layer P1 if time allows. Does that split look right to you?"*

You have now made the interviewer a co-signer of your scope. If you don't finish P1, you
both already agreed that was fine. That sentence is worth more than any code you write.

---

## Part 5 — Minutes 10–20: the skeleton you type from memory

**This is the antidote to blank-page paralysis.** You should be able to type this structure
without thinking, for any problem. It's the same every time.

```
project/
├── NOTES.md              your scope tiers (already written)
├── README.md             write this LAST, 5 minutes
├── demo.py               the runnable entry point - CREATE IT FIRST
├── test_service.py       tests
└── <domain>/
    ├── __init__.py
    ├── models.py         dataclasses + enums. No logic.
    ├── exceptions.py     custom exception types. 6 lines.
    ├── store.py          thread-safe state. Owns the lock.
    └── service.py        the orchestration / public API
```

**The rule: `demo.py` exists and runs at minute 12.** Before any real logic. Stub every
method with `pass` or `raise NotImplementedError`, import them all, and run it. Now you have
a working program and every subsequent minute makes it better rather than hoping it all
comes together at the end.

The concrete typing order:

1. `exceptions.py` — 30 seconds, and it makes you look thorough immediately.
2. `models.py` — dataclasses and enums. This forces you to name your domain, which is where
   good design comes from.
3. `store.py` / `service.py` — stub the public methods with the right signatures.
4. `demo.py` — import and call the stubs. **Run it.**

See [`toolkit/skeleton/`](toolkit/skeleton/) for the exact files to copy, and
[`toolkit/primitives.py`](toolkit/primitives.py) for the thread-safe building blocks worth
having in muscle memory.

### The single most useful habit

Write `models.py` before `service.py`. Every time. Naming your entities
(`Task`, `TaskStatus`, `Priority`) makes the rest of the design fall out almost
automatically, and it's the fastest possible way to look like you've done this before.

---

## Part 6 — Minutes 20–55: build the core

### Design moves that score, cheaply

**Interfaces where the problem hints at variation.** If the problem says "support different
eviction policies" or "different rate limiting algorithms", that is a direct instruction to
use an ABC:

```python
class RateLimitStrategy(ABC):
    @abstractmethod
    def allow(self, key: str) -> bool: ...

class TokenBucket(RateLimitStrategy): ...
class SlidingWindow(RateLimitStrategy): ...
```

Two implementations of one interface earns almost all the design credit available. Three
earns nothing extra. Build two and *mention* the third.

**Dependency injection over hardcoding.** `Scheduler(store=InMemoryStore())` lets you say
"and I'd swap in a Redis-backed store here" without writing it.

**Composition over inheritance.** Interviewers ask about this. Deep hierarchies are a
negative signal.

**Don't over-engineer.** No abstract factory. No observer pattern for a two-line callback.
No `BaseAbstractManagerFactory`. Over-engineering reads as inexperience just as loudly as
under-engineering does.

### Concurrency moves that score

This is your topic — this is where you should visibly outclass the average candidate.

**One clear owner per piece of shared state.** The class that owns the data owns the lock.
Callers never see it. Never expose a `.lock` attribute.

```python
class TaskStore:
    def __init__(self):
        self._tasks: dict[str, Task] = {}
        self._lock = threading.RLock()      # RLock: methods may call each other

    def add(self, task: Task) -> None:
        with self._lock:
            self._tasks[task.id] = task
```

**Say the check-then-act sentence.** When you write a method that checks a condition then
acts on it, say out loud: *"This is a check-then-act, so the check and the mutation have to
be inside one lock acquisition."* That one sentence marks you as someone who has actually
debugged a race.

**Use `queue.Queue`, don't hand-roll.** Reaching for `Queue` and `ThreadPoolExecutor`
signals judgement. Hand-rolling a `Condition`-based queue when the stdlib has one signals
the opposite — unless they explicitly asked you to build the primitive.

**Design shutdown from the start.** Almost nobody does this, and it's the most common
follow-up question:

```python
def shutdown(self, wait: bool = True, timeout: float = 5.0) -> None:
    self._stop.set()                      # cooperative signal
    for worker in self._workers:
        worker.join(timeout=timeout)      # ALWAYS with a timeout
```

**Never hold a lock across I/O or a callback.** Compute inside the lock, act outside it.
Say this out loud when you do it.

### The most common concurrency mistakes in this round

| Mistake | Fix |
|---|---|
| Unguarded `dict`/`list` mutated by workers | one lock in the owning class |
| Check-then-act split across two lock blocks | one `with self._lock:` around both |
| `while True: q.get()` with no shutdown path | sentinel, or `get(timeout=...)` + `Event` |
| Worker body not wrapped in `try/except` | one exception kills the worker silently |
| `time.sleep()` used to "synchronise" | `Event`, `Condition`, or `Queue` |
| Lock held while calling a user callback | copy what you need, release, then call |
| No `maxsize` on the queue | unbounded memory; set it and say "backpressure" |

---

## Part 7 — Minutes 55–70: tests

**Do not skip this. Ever.** Tests are the cheapest points on the board and most candidates
run out of time before writing any, which means writing five puts you ahead of the field.

Plain `unittest` or bare asserts in a function — no pytest needed, no fixtures, no mocks.

**Write these five, in this order:**

1. **Happy path** — the core flow does the thing.
2. **Edge case** — empty input, capacity of one, duplicate id.
3. **Error case** — invalid input raises your custom exception.
4. **Concurrency** — N threads hammering it; assert the invariant holds.
5. **Shutdown** — the system stops cleanly and joins.

The concurrency test is the one that impresses. It's also formulaic — memorise this shape:

```python
def test_concurrent_writes(self):
    service = Service()
    errors = []

    def worker(n):
        try:
            for i in range(100):
                service.do_thing(f"key-{n}-{i}")
        except Exception as exc:
            errors.append(exc)

    threads = [threading.Thread(target=worker, args=(i,)) for i in range(10)]
    for t in threads: t.start()
    for t in threads: t.join(timeout=10)

    self.assertFalse(errors, f"errors under concurrency: {errors}")
    self.assertEqual(service.count(), 1000)      # <- assert the INVARIANT
```

**Assert invariants, never ordering.** `assertEqual(counter, 1000)`, `assertLessEqual(len(cache), capacity)`,
`assertEqual(sorted(results), expected)`. Any test that asserts a specific thread ordering
is a test that will fail in front of the interviewer.

---

## Part 8 — Minutes 80–90: land the plane

At **1:20 you stop writing features.** Non-negotiable. Then:

1. **Run everything.** `python demo.py`. `python -m unittest test_service.py -v`. Fix
   anything broken. This is the only thing that matters now.
2. **Delete dead code.** Commented-out blocks, unused imports, `print` debugging. Two
   minutes, and it visibly raises the quality of the whole submission.
3. **Write `README.md`** — five minutes, and it frames how they read your code:

```markdown
# Task Scheduler

## Run
    python demo.py
    python -m unittest discover -v

## Design
- `TaskStore` owns all shared state behind one RLock; nothing else locks.
- `WorkerPool` consumes from a bounded `queue.Queue` (backpressure) and
  supports cooperative shutdown via an `Event`.
- `RetryPolicy` is an interface so backoff strategies can vary.

## Thread safety
- Store mutations are guarded by a single RLock.
- Status transitions are check-then-act, done inside one lock acquisition.
- Workers catch all exceptions so a bad task can't kill a worker.

## Done
- P0: submit, prioritise, execute, query status
- P1: retries with exponential backoff

## Not done (and how I'd add it)
- Persistence: `TaskStore` is already an interface; add a SQLite implementation.
- Cron scheduling: add a `Trigger` abstraction alongside the existing delay field.
- Distributed workers: replace the in-process Queue with a broker.
```

That last section — **"Not done, and how I'd add it"** — converts your unfinished scope
from a weakness into evidence of judgement. Never leave it out.

---

## Part 9 — Talking while you code

Machine coding is silent for long stretches, and silence gets read as confusion. You don't
need a running monologue — just narrate at decision points.

**Sentences worth having ready:**

- *"I'll use an RLock here because these methods call each other."*
- *"This is a check-then-act, so both steps go inside one lock."*
- *"I'm bounding this queue so a fast producer applies backpressure instead of eating memory."*
- *"There's no way to kill a thread in Python, so shutdown is cooperative via this Event."*
- *"I'm making this an interface because you mentioned multiple strategies — here are two,
  and a third would just be another subclass."*
- *"I'm deliberately not building persistence; it's a P2 and the store is already an
  interface, so it's a drop-in."*

**When you get stuck — say it.** *"I'm deciding between X and Y; I'll go with X because it's
simpler and I can refactor if we need Y."* Then move. Interviewers help candidates who
think out loud. They cannot help a silent one.

---

## Part 10 — Recovery: when it's going wrong

**"I'm at minute 60 and the core doesn't work."**
Stop. Cut every feature. Get the single simplest happy path running, even if it's ugly.
Then write two tests. A working 40% beats a broken 80%, and it isn't close.

**"I've hit a bug I can't find."**
Time-box it to five minutes. Then comment out the broken feature, make everything else run,
and say: *"There's a bug in the retry path; I've isolated it to this method and I'd add a
test around the state transition to pin it down."* Diagnosing your own bug out loud scores
better than silently thrashing.

**"I over-engineered and I'm drowning in abstractions."**
Delete them. Genuinely. Inline the abstract classes, keep one concrete implementation, get
it running. Nobody has ever been rejected for insufficient inheritance.

**"I don't understand the problem."**
Ask. At minute 5, at minute 30, at minute 60. Asking a clarifying question is never a
negative signal. Building the wrong thing silently for an hour is fatal.

**"I finished P0 at minute 40."**
Don't add features yet. Write your tests first, then your README, *then* pick up P1. Locking
in the points you already have beats gambling them on more scope.

---

## Part 11 — Your practice plan

Fear dies from repetition, not from reading. This repo gives you the reps.

**Week 1 — learn the shape.**
Read [`worked_example/`](worked_example/) end to end. It's a complete 90-minute build with
narration of what was written when and why. Then re-type it from scratch yourself, looking
only at your notes. Twice.

**Week 2 — timed runs, generous clock.**
Do problems 1–3 from [`problems/`](problems/) at **120 minutes** each. Use the clock plan.
Score yourself against [`RUBRIC.md`](RUBRIC.md) honestly. Run
`python machine_coding/problems/check.py N` to test your work.

**Week 3 — timed runs, real clock.**
Problems 4–6 at **90 minutes**. Then redo problem 1 — you'll be shocked how much faster it
is. That feeling is the fear leaving.

**Every session, without exception:**
- Set an actual visible timer.
- Write `NOTES.md` with tiers before typing code.
- Have `demo.py` running by minute 20.
- Stop coding at the 90% mark whether you're done or not.
- Score yourself with the rubric.

**The drill that pays most:** set a 20-minute timer and *only* build the skeleton —
`models.py`, `exceptions.py`, stubs, a running `demo.py`. Do this for five different
problems. After five reps the blank page stops being blank, and that is the specific thing
you're afraid of.

---

## What's in this folder

| Path | What it is |
|---|---|
| [`RUBRIC.md`](RUBRIC.md) | Score your own practice run the way an interviewer would |
| [`toolkit/skeleton/`](toolkit/skeleton/) | The file structure to copy at minute 10 |
| [`toolkit/primitives.py`](toolkit/primitives.py) | Thread-safe building blocks worth memorising |
| [`worked_example/`](worked_example/) | A complete, narrated 90-minute build |
| [`problems/`](problems/) | 6 full problems with tiered requirements |
| [`problems/check.py`](problems/check.py) | Tests to verify your solutions |
| [`problems/solutions/`](problems/solutions/) | Reference implementations |

---

## The one paragraph to reread before you walk in

You will not finish. Nobody finishes — the problems are scoped so you can't. You are being
measured on whether the part you *did* build runs, is thread-safe, is tested, and is
structured such that the missing parts are obviously easy to add. Write your tiers down in
the first ten minutes, get something running by minute twenty, protect the working core
above all else, and stop coding with ten minutes left. Do that and you pass, even at 50% of
the feature list.
