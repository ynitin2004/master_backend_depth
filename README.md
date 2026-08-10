# Backend Interview Prep — Python Concurrency

Two complete, runnable courses. Standard library only, no installs, no internet.
Built and verified on **Python 3.12.4**.

```bash
python multithreading/examples/01_first_thread.py       # start here
python multithreading/exercises/check.py                # test your answers
python machine_coding/problems/check.py --solution      # verify the references
```

---

## [multithreading/](multithreading/) — learn the topic

Zero to mastery in 16 modules. Read a concept, run its example, then solve the problems.

| | |
|---|---|
| [README.md](multithreading/README.md) | The course. Mental model, the GIL, all 16 modules, cheat sheet, ten rules. |
| [examples/](multithreading/examples/) | 16 runnable scripts — threads, locks, conditions, queues, deadlock, pools, patterns, debugging. |
| [exercises/](multithreading/exercises/) | 15 problems (easy → interview-hard) with guided starters. |
| [exercises/check.py](multithreading/exercises/check.py) | Self-checking runner. Forces preemption to catch races that pass once. |
| [INTERVIEW_QA.md](multithreading/INTERVIEW_QA.md) | 28 questions in three tiers, plus senior/junior signal lists. |

**Run this one first** — [`13_gil_benchmark.py`](multithreading/examples/13_gil_benchmark.py)
measures the GIL on your own machine and answers half of all threading interview questions
with numbers instead of memorised claims.

## [machine_coding/](machine_coding/) — pass the round

The 90-minute build round is a *process* problem, not a knowledge problem. This is the
process, plus the reps.

| | |
|---|---|
| [README.md](machine_coding/README.md) | The playbook: scoring, the minute-by-minute clock, what to say, how to recover. |
| [RUBRIC.md](machine_coding/RUBRIC.md) | Score your own practice run the way an interviewer would. |
| [toolkit/skeleton/](machine_coding/toolkit/skeleton/) | The file structure to type at minute 10. Runs as-is. |
| [toolkit/primitives.py](machine_coding/toolkit/primitives.py) | Nine thread-safe building blocks worth memorising. |
| [worked_example/](machine_coding/worked_example/) | A complete task scheduler, narrated: what was written when, and why. |
| [problems/](machine_coding/problems/) | 6 full problems with tiered requirements and exact API contracts. |
| [problems/check.py](machine_coding/problems/check.py) | Verifies your solution; P1 gaps report as SKIP, not failure. |

---

## Suggested path

| Week | Do this |
|---|---|
| 1 | `multithreading/` modules 1–9, then exercises 1–8 |
| 2 | modules 10–16, exercises 9–15, read `INTERVIEW_QA.md` aloud |
| 3 | `machine_coding/README.md`, then re-type the worked example twice |
| 4 | Problems 5, 1, 4 at 120 min each. Score with the rubric every time. |
| 5 | Problems 3, 2, 6 at 90 min. Then redo problem 5 cold. |

## Verified

Every example, exercise solution, and reference solution runs clean:

```bash
python multithreading/exercises/check.py --solution      # 15/15
python machine_coding/problems/check.py --solution       # 6/6, P0 and P1
cd machine_coding/worked_example && python -m unittest test_scheduler.py   # 19 tests
python machine_coding/toolkit/primitives.py              # self-test
```
