# Self-Evaluation Rubric

Score every practice run. Be harsh — a generous self-score is a wasted rep.

Fill this in **immediately** when your timer stops, before you fix anything.

---

## Section A — Does it work? (40 points)

The gate. If you score under 25 here, nothing else matters and you should stop the
post-mortem and just note "core didn't run" as the only lesson.

| Pts | Item | Score |
|---|---|---|
| 10 | `python demo.py` runs with no error, from a clean shell | |
| 10 | Tests run and pass (`python -m unittest ...`) | |
| 10 | Every P0 requirement is demonstrably working | |
| 5 | The demo actually *shows* the features (not just "no crash") | |
| 5 | No `NotImplementedError`, no commented-out blocks, no debug prints left | |

**Section A: ___ / 40**

---

## Section B — Concurrency correctness (25 points)

Your topic. You should be scoring 20+ here every single time.

| Pts | Item | Score |
|---|---|---|
| 6 | Every piece of shared mutable state is guarded by a lock | |
| 5 | No check-then-act split across two lock acquisitions | |
| 4 | Locks acquired in a consistent order (or only one lock is ever held) | |
| 4 | Clean cooperative shutdown exists and is joined with a timeout | |
| 3 | Worker bodies wrapped in `try/except` so one bad task can't kill a worker | |
| 3 | No lock held across I/O, `sleep`, or a user callback | |

**Section B: ___ / 25**

**Red flags — subtract 5 each, they're worse than missing points:**
- [ ] `time.sleep()` used to synchronise threads
- [ ] a `.lock` attribute exposed publicly for callers to use
- [ ] unbounded queue where a producer can outrun consumers
- [ ] `while True:` worker loop with no way out

---

## Section C — Design (20 points)

| Pts | Item | Score |
|---|---|---|
| 5 | Clear separation: models / storage / service. No god class. | |
| 4 | An interface (ABC) exactly where the problem hinted at variation | |
| 3 | At least two implementations behind that interface | |
| 3 | Dependencies injected, not hardcoded inside constructors | |
| 3 | Domain-accurate naming; enums instead of magic strings | |
| 2 | Custom exception types | |

**Section C: ___ / 20**

**Red flags — subtract 3 each:**
- [ ] over-engineering: abstractions with exactly one implementation and no stated reason
- [ ] inheritance used where composition was the obvious fit
- [ ] a single file over ~300 lines

---

## Section D — Tests (10 points)

| Pts | Item | Score |
|---|---|---|
| 3 | At least 4 tests exist and pass | |
| 3 | One is a genuine multi-threaded test | |
| 2 | Tests assert invariants, not thread ordering | |
| 2 | An error/edge case is covered, not just the happy path | |

**Section D: ___ / 10**

---

## Section E — Communication (5 points)

| Pts | Item | Score |
|---|---|---|
| 2 | `NOTES.md` with P0/P1/P2 tiers, written before coding | |
| 2 | `README.md` with run instructions and design notes | |
| 1 | A "not done, and how I'd add it" section | |

**Section E: ___ / 5**

---

## Total: ___ / 100

| Score | Reading |
|---|---|
| **85+** | Strong hire. You'd pass at a senior bar. |
| **70–84** | Hire. Solid round. |
| **55–69** | Borderline. Usually: core worked but no tests, or a visible race. |
| **40–54** | Weak. Usually: ran out of time because scope wasn't cut early. |
| **< 40** | Core didn't run. Only one lesson matters — see below. |

---

## Post-mortem (fill this in — it's the actual point)

**Where was I at each milestone?**

| Milestone | Target | Actual | |
|---|---|---|---|
| Scope written, tiers agreed | 0:10 | ___ | |
| `demo.py` runs (stubs fine) | 0:20 | ___ | |
| Happy path works end to end | 0:55 | ___ | |
| Tests written and passing | 1:10 | ___ | |
| Stopped coding | 1:20 | ___ | |

**The single biggest time sink was:** ________________________________

**What I should have cut, and when:** ________________________________

**Concurrency bug I found afterwards (be honest):** ________________________________

**One thing to do differently next run:** ________________________________

---

## Diagnosing your pattern

Run this after three or four practice sessions and look for the repeat offender.

| Symptom | Root cause | The fix |
|---|---|---|
| Never reach the tests | Scope not cut at 0:55 | Set a phone alarm for 0:55. When it fires, stop adding features. |
| `demo.py` broken at the end | Didn't run it every 10 min | Run it after every single method you finish. |
| Score low on design | Jumped straight to logic | Always write `models.py` first. Always. |
| Score low on concurrency | Bolted locks on at the end | Add the lock the same minute you create the shared dict. |
| Ran out of time on P0 | Over-engineered early | One concrete class first. Extract the interface only after two exist. |
| Blank-page freeze | No rehearsed skeleton | Do the 20-minute skeleton-only drill five times. |
| Panic mid-round | No milestones to check against | Memorise the clock. Knowing you're on track is the whole cure. |

---

## The one-line version

**Working and tested at 60% scope beats broken at 90% — every time, without exception.**
