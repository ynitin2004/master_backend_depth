# <Problem Name>

Write this BEFORE you write any code. Two minutes. Then say to the interviewer:
"I'll build P0 first and make sure it's solid and tested, then layer P1 if time
allows — does that split look right?"

## P0 — must work (target 0:55)
- [ ] <the single core flow, end to end>
- [ ] <the second essential operation>
- [ ] <query / read path>

## P1 — if time (target 1:20)
- [ ] <a feature that layers cleanly on P0>
- [ ] <another>

## P2 — mention, don't build
- persistence
- distributed / multi-process
- metrics export, admin API

## Assumptions
- in-memory, single process
- thread-safe: calls arrive from multiple threads
- <domain assumption, e.g. "ids are client-supplied and unique">

## Clarifying questions asked
- Q: In-memory and single process?              A:
- Q: Should this be thread-safe?                A:
- Q: Breadth of features or depth on the core?  A:

## Design decisions (fill in as you go — this becomes your README)
- <e.g. "one RLock in Store; nothing else locks">
- <e.g. "EvictionPolicy is an ABC; LRU and FIFO implemented">
