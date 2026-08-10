# AI Engineer Interview — 100 Questions, Easiest → Hardest

**Candidate:** Nitin Yadav — Backend / GenAI Engineer
**Target:** AI Engineer, ₹12 LPA (India, ~1 YoE + 2026 grad)
**Format:** 2-hour technical round, written from the interviewer's chair.

Every question below carries four things:

| Field | Meaning |
|---|---|
| **Probes** | What I'm actually measuring. Rarely the literal question. |
| **Want** | What earns a hire. |
| **🚩** | What loses it. |
| **You** | A model answer in your voice, using your real projects. |

> **A note on the 100.** No interviewer asks 100 questions in 2 hours. I'd ask
> **30–40** and go deep on your answers. This is a *bank* — the full space I could
> pull from. Prepare all of it, expect a third of it.

---

# How I'd score you for ₹12 LPA

At this band I'm not looking for a researcher. I'm looking for someone who has
**shipped an LLM system to real users and knows why it broke.**

| Weight | Signal | What ₹12 LPA looks like |
|---|---|---|
| ★★★★★ | **You built it, not followed a tutorial** | You can explain a decision you *changed your mind about* and why |
| ★★★★★ | **Production instincts** | Latency, cost, failure modes, retries, idempotency come up unprompted |
| ★★★★ | **RAG depth** | Chunking → retrieval → reranking → grounding → **eval**. Most candidates die at "eval". |
| ★★★★ | **Python + backend fundamentals** | Async, Celery, PostgreSQL indexing — not just LangChain glue |
| ★★★ | **Honest calibration** | "I haven't done that, here's how I'd approach it" beats a confident wrong answer, every time |
| ★★★ | **Debugging narrative** | One specific bug, in detail, with the fix |
| ★★ | **Communication** | Structure, no rambling, checks whether I want depth |

**Bands I'd assign:**

- **₹8–10 LPA** — knows the APIs, can build a RAG demo, vague on evals/cost/failure.
- **₹12–14 LPA** ← *your target* — shipped to production, has opinions from scars, measures things, honest about gaps.
- **₹18 LPA+** — has owned a system end-to-end at scale, designed evals from scratch, made real cost/quality tradeoffs with numbers.

**The single fastest way to lose the offer:** inflating a resume number you can't
defend. See the landmines section — read it before anything else.

---

# ⚠️ The 8 landmines in your resume

I will attack these. Every competent interviewer will. Have an answer ready for
each **before** you walk in.

### 1. "improved query response time by 35% … horizontal sharding" (SS Innovations)

**This is the biggest one.** Horizontal sharding in PostgreSQL is a serious
architectural move (Citus, or app-level shard routing). At your experience level,
I will assume you mean **declarative partitioning** and I will ask.

- If it was **partitioning** (`PARTITION BY RANGE (created_at)` etc.) — say
  *partitioning*. It's still a good answer, and the honesty scores.
- If it was genuinely Citus/multi-node — be ready for: shard key choice,
  co-location, cross-shard joins, rebalancing.
- **Never** let me discover the word was wrong. Correct it yourself, early:
  *"Small correction on my resume wording — that was table partitioning, not
  true horizontal sharding. Let me tell you what we actually did."*
  That sentence alone can save the interview.

### 2. "73% improvement in query response time" (SimplifyAI)

I'll ask: **73% of what, measured how?** Have ready: the baseline number
(e.g. "p95 was 1.4s"), the after number, the tool (`EXPLAIN ANALYZE`, APM,
logs), and the actual change (index added? N+1 removed? query rewritten?).
"It felt faster" is a fail.

### 3. "reducing manual processing time by ~40%"

Business metric. Who measured it? Was it a time-and-motion estimate from the ops
team, or instrumented? Saying *"that was the operations team's estimate, not
something I instrumented"* is a **strong** answer — it shows you know the
difference.

### 4. Feb 2026 – Present = ~6 months at SS Innovations

Short tenure. I'll wonder about the SimplifyAI → SS Innovations move. Have a
clean, non-negative reason (scope, domain, full-time conversion, product
ownership). Never criticise a past employer.

### 5. You're still a 2026 graduate

I'll check that you can commit full-time and that college obligations are done.
Answer crisply.

### 6. Node.js at SS Innovations vs Python/FastAPI at SimplifyAI

Your current job is Node. The role is AI Engineer, probably Python. I'll test
whether your Python is stale. **Revise Python async and FastAPI specifically.**
Frame it as: *"Python is my primary language for AI work; the current role is
Node for the existing codebase, but my GenAI work — Pitcher, the SimplifyAI
platform — is all Python/FastAPI."*

### 7. "Kafka, AWS ECS" in skills but nowhere in experience

I'll ask. If you've only read about them, say so: *"I've used Kafka in a side
project / studied it; I haven't run it in production."* Getting caught bluffing
on one skill makes me doubt all the others.

### 8. Two RAG systems on the resume, no eval story anywhere

**This is your biggest opportunity.** Nobody at your band talks about evaluation.
If you walk in with a real answer to *"how did you know the RAG was good?"* you
jump a band instantly. Section E covers it — prioritise Q60–Q68.

---

# The 2-hour flow

```
0:00  A. Warm-up & resume walkthrough        Q1–10     ← rapport + landmines
0:12  B. Python fundamentals                 Q11–22    ← is the Python real?
0:25  C. Async, concurrency, Celery          Q23–34    ← your Celery/WebSocket claims
0:40  D. LLM fundamentals & prompting        Q35–48    ← baseline GenAI literacy
0:55  E. RAG deep dive                       Q49–68    ← THE section for your profile
1:20  F. Agents, tool-calling, LangGraph     Q69–78    ← Pitcher + LangGraph claim
1:32  G. Realtime voice & WebSockets         Q79–85    ← Pitcher deep dive
1:40  H. Data, caching, scale                Q86–92
1:47  I. Evals, cost, safety, prod ops       Q93–98    ← the band-jumper
1:53  J. Live coding + design + close        Q99–100
```

---

# Section A — Warm-up & resume walkthrough (Q1–10)

*I'm calibrating how you communicate and finding threads to pull on later.*

### Q1. Walk me through your background in two minutes.

**Probes:** Can you compress? Do you lead with what matters?
**Want:** Chronological, ends on why *this* role. Names 2–3 concrete systems with outcomes. Under 2 min.
**🚩** Reciting the resume line by line. Starting with school. Running past 4 minutes.
**You:** *"I'm a backend engineer who moved into GenAI about a year ago. At SimplifyAI I owned the backend for an HR platform — Python, FastAPI — and built RAG pipelines for document intelligence, plus a Celery/Redis layer for long-running LLM jobs. Since February I've been at SS Innovations on hospital systems, where I built a RAG agent that reads Excel sheets and auto-fills daily hospital reports. Outside work my main project is Pitcher — a real-time voice agent that generates a slide deck and presents it live, using a realtime speech model with tool-calling to drive the UI. I'm looking for a role where the AI work is the core product, not a feature bolted on."*

### Q2. Which project are you proudest of, and why?

**Probes:** Do you have taste? Do you value hard problems or shiny ones?
**Want:** Picks by *difficulty or impact*, not by how cool it looks. Names the hardest sub-problem.
**🚩** "All of them." Picking the one with the nicest UI.
**You:** Pitcher — and name the hard part: **barge-in**. Interrupting an AI mid-sentence is a latency and state-management problem, not a model problem.

### Q3. What's the largest scale you've personally worked with — users, requests, data?

**Probes:** Honesty. I already know a hospital ops tool isn't web-scale.
**Want:** Real numbers, and a clear statement of the limits. "10+ hospital sites, tens of thousands of records, dozens of concurrent users."
**🚩** Inflating to "millions." I'll ask a follow-up you can't answer.
**You:** Give the honest number, then add what you *did* have to engineer for: concurrent WebSocket updates, long-running LLM jobs, DB query performance.

### Q4. Tell me about the DHR RAG agent. What does it actually do, end to end?

**Probes:** Whether you can explain your own system's data flow.
**Want:** Upload → parse Excel → chunk/normalise → embed or structure → LLM extracts fields → validate → write to form → human review. Mentions validation and the human in the loop.
**🚩** Jumping straight to "we used an LLM." Skipping validation.
**You:** Walk the pipeline. Then volunteer the failure mode: *"The hardest part was that Excel sheets from different hospitals had different column names and merged cells — that's a normalisation problem before it's an LLM problem."*

### Q5. Was that actually RAG, or was it structured extraction?

**Probes:** ⚠️ **Precision of vocabulary.** Many candidates label everything RAG.
**Want:** An honest taxonomy. If you retrieved relevant rows/context before generating → RAG. If you stuffed a sheet into a prompt and asked for fields → that's *extraction*, and that's fine.
**🚩** Defending the label instead of describing the system.
**You:** *"It's retrieval plus extraction. We retrieve the relevant rows and prior report context, then do schema-constrained field extraction. I'd honestly call the extraction step the harder half."*

### Q6. Why did you leave SimplifyAI after five months?

**Probes:** Stability, and whether you badmouth.
**Want:** Forward-looking. Scope, ownership, domain.
**🚩** Criticising the company, pay, or a manager.
**You:** Keep it short and positive. Don't over-explain — length reads as defensiveness.

### Q7. You're graduating in 2026 — are you full-time available?

**Want:** A crisp yes with dates. Any pending obligations stated upfront.
**🚩** Vagueness. It reads as a hidden constraint.

### Q8. Your current role is Node.js, but this role is Python-first. Talk to me about that.

**Probes:** Is your Python current or decaying?
**Want:** Clear framing + evidence of recent Python.
**You:** *"Python is my language for AI work — SimplifyAI was FastAPI end to end, and Pitcher is FastAPI with a WebSocket relay. The Node work at SS Innovations is because that's the existing stack. I'm actively keeping Python sharp — I've been working through concurrency internals recently, threading versus asyncio versus multiprocessing and where the GIL actually bites."*
*(That last clause is true — you just built that repo. Use it.)*

### Q9. What's an AI/LLM concept you found genuinely hard, and how did you get it?

**Probes:** Self-awareness and learning method.
**Want:** A real concept with a real struggle. Good picks: why cosine similarity retrieves *related but useless* chunks; why chunk boundaries destroy answers; why an agent loops forever.
**🚩** "Nothing was hard." A textbook definition with no struggle in it.

### Q10. What are you looking for in your next role?

**Want:** Specific and mutual. Ties to what this company does.
**🚩** Only money. Only "learning" (too vague).

---

# Section B — Python fundamentals (Q11–22)

*Is the Python real, or is it LangChain glue?*

### Q11. List vs tuple vs set — when do you reach for each?

**Want:** Mutability, hashability, O(1) membership for sets, tuple as dict key / record.
**🚩** Only "tuples are immutable" with no use case.

### Q12. What does the GIL do, and when does it actually hurt you?

**Probes:** ⚠️ **Near-certain question.** Everyone half-knows this.
**Want:** One mutex, only one thread runs Python bytecode at a time. Released on I/O, `sleep`, locks, and in many C extensions. So: **I/O-bound → threads help; CPU-bound → they don't, use processes.** Bonus: it's a CPython implementation detail; 3.13+ has an experimental free-threaded build.
**🚩** "The GIL makes Python thread-safe." It does the opposite of what people think.
**You:** *"Only one thread executes bytecode at a time, so threads buy you nothing for CPU-bound work — but the GIL is released during I/O, which is where all the real gain comes from. In our stack that's exactly right: LLM calls and DB queries are all waiting, so threads and async both work. Anything CPU-bound — heavy parsing, local embedding — goes to a process pool or a separate worker."*

### Q13. `counter += 1` from two threads. Safe?

**Want:** No — three bytecodes (load, add, store); a switch can land mid-sequence and you lose increments. Needs a lock.
**🚩** "The GIL makes it atomic."
**You:** Mention *check-then-act* as the more dangerous real-world form: `if key not in cache: cache[key] = expensive()` — two threads both build it.

### Q14. Difference between `is` and `==`?

**Want:** Identity vs equality. `is None` is the correct idiom. Small-int/string interning is an implementation detail you shouldn't rely on.

### Q15. What's a decorator? Write one that retries on failure.

**Want:** `functools.wraps`, `*args/**kwargs`, exponential backoff **with jitter**, a cap on attempts, re-raise at the end.
**🚩** Forgetting `wraps`. Retrying without a cap. No jitter.
**You:** Say the jitter reason out loud: *"Without jitter every failing client retries at the same instant and stampedes the service that's trying to recover."*

### Q16. `@staticmethod` vs `@classmethod` vs instance method?

**Want:** `cls` as an alternate constructor (`Model.from_config(...)`), staticmethod as namespaced utility.

### Q17. Shallow vs deep copy — when has it bitten you?

**Want:** Nested mutable state; `copy.deepcopy`; mutable default arguments (`def f(x=[])`) as the classic bug.

### Q18. What are generators, and why would you use one in an LLM pipeline?

**Probes:** Do you connect language features to your domain?
**Want:** Lazy evaluation, constant memory over large sequences. **Direct application: streaming LLM tokens to the client, and chunking a huge document without loading it all.**
**You:** Tie it to Pitcher's audio streaming or to chunking a large PDF.

### Q19. `dataclass` vs Pydantic model — when do you use which?

**Probes:** FastAPI depth.
**Want:** dataclass = plain container, no validation. Pydantic = runtime validation, coercion, serialisation, JSON Schema — which is why FastAPI uses it, and why it's the natural fit for **validating LLM structured output**.
**You:** *"In the interview-prep platform I used the Pydantic schema both to validate the request and to define the JSON shape the LLM had to return — same schema, two jobs."*

### Q20. How do you manage secrets and config in a FastAPI service?

**Want:** Env vars, `pydantic-settings`, never in git, `.env` gitignored, secrets manager in prod, different keys per environment, rotation.
**🚩** Hardcoded API keys. "We committed the .env but it was a private repo."

### Q21. How do you structure a FastAPI project past 20 endpoints?

**Want:** Routers by domain, `services/` for logic, `repositories/` for data, Pydantic schemas separate from ORM models, dependency injection via `Depends`, thin route handlers.
**🚩** Everything in `main.py`.

### Q22. What does `Depends()` actually do, and why is it useful for testing?

**Want:** DI — resolves and caches per request; `dependency_overrides` lets you swap a real LLM client or DB session for a fake in tests.
**🚩** Never having tested anything.

---

# Section C — Async, concurrency, Celery (Q23–34)

*Your resume claims Celery + Redis, async, and WebSockets. Let's see.*

### Q23. `async def` vs a thread — what's the real difference?

**Probes:** ⚠️ Whether FastAPI async was cargo cult.
**Want:** **Cooperative vs preemptive.** async switches only at `await`; threads switch anywhere. So async needs far fewer locks but **one blocking call freezes the entire event loop**.
**🚩** "async makes it faster."
**You:** *"The failure mode I watch for is a sync library sneaking into an async handler — one blocking `requests.post` in an async route and the whole loop stalls for every user, not just that request."*

### Q24. In FastAPI, what's the difference between `def` and `async def` for a route?

**Probes:** ⚠️ **Most candidates get this wrong.** Great differentiator.
**Want:** `async def` runs **on the event loop** — blocking code there is fatal. Plain `def` is run **in a threadpool** by Starlette, so blocking is safe there. So: async library → `async def`. Blocking library → plain `def`, or `await asyncio.to_thread(...)`.
**You:** Say this cleanly and I'll mark you up. Very few juniors know it.

### Q25. You need to call 50 LLM APIs. How?

**Want:** `asyncio.gather` with a `Semaphore` to cap concurrency; `return_exceptions=True` so one failure doesn't kill the batch; per-call timeout; retry with backoff+jitter; respect provider rate limits.
**🚩** A serial `for` loop. Unbounded `gather` over 50 (you'll get rate-limited or blow memory).
**You:** *"Semaphore around it — the provider's rate limit is the real constraint, not my CPU."*

### Q26. Walk me through your Celery + Redis setup at SimplifyAI. Why was it needed?

**Probes:** ⚠️ Resume claim. Go deep here.
**Want:** LLM jobs take 30s–5min; HTTP requests shouldn't hold that. So: enqueue → return a job id immediately → client polls or gets a webhook/WebSocket. Redis as broker; result backend named separately.
**🚩** Not knowing broker vs result backend are different roles.

### Q27. A Celery worker dies mid-task. What happens?

**Probes:** Production instincts. **This is a band-defining question.**
**Want:** Default `acks_early` → the message is already acked → **the task is lost**. Fix: `acks_late=True` so it's re-delivered — but then the task **must be idempotent**, because it may run twice. Plus `visibility_timeout` on Redis, and a max retry policy.
**🚩** "Celery handles it."
**You:** *"That's why the task has to be idempotent — for our LLM jobs we keyed on a job id and checked whether the result already existed before spending another API call. Re-running an LLM task isn't just slow, it's money."*

### Q28. How do you make an LLM task idempotent?

**Want:** Deterministic job id (hash of input), check-then-write guarded atomically, `INSERT ... ON CONFLICT DO NOTHING`, or a Redis `SETNX` lock. State machine: `PENDING → RUNNING → DONE`, with a guarded transition.
**You:** Connect to Q13 — *"the check and the write have to be one atomic step, or two workers both decide it's not done."*

### Q29. Celery `prefork` vs `gevent` vs `threads` — which for LLM calls, and why?

**Want:** LLM calls are I/O-bound waiting on the network → `gevent`/`eventlet`/threads give far higher concurrency per worker. `prefork` is for CPU-bound. Also `worker_prefetch_multiplier=1` for long tasks, so one worker doesn't hoard the queue.
**🚩** Not knowing the pool types exist.

### Q30. How do you stop a long-running task in Python?

**Want:** **You can't kill a thread.** Cooperative cancellation — the task checks an `Event`/flag and returns. Celery's `revoke` only prevents un-started tasks unless you `terminate=True`, which is a signal and unsafe mid-write.
**🚩** Thinking `future.result(timeout=5)` cancels anything. It gives up *waiting*; the work continues.

### Q31. Race condition — define it and give one from your own work.

**Want:** Result depends on unpredictable timing. Real example from your inventory system: two WebSocket clients updating the same instrument record concurrently.
**🚩** A textbook definition with no personal example.

### Q32. Two users update the same inventory record simultaneously. How do you handle it?

**Probes:** ⚠️ Directly on your resume ("concurrent data updates").
**Want:** **Optimistic locking** — a `version` column, `UPDATE ... WHERE version = ?`, 0 rows affected → conflict → retry or surface to the user. Or pessimistic `SELECT FOR UPDATE` for short critical sections. Name the tradeoff: optimistic for low contention, pessimistic for high.
**🚩** "The database handles it." Last-write-wins with no awareness that data is being lost.

### Q33. How do you scale WebSockets past one server instance?

**Want:** WebSocket state is per-instance; a broadcast on server A never reaches a client on server B. Fix: a shared pub/sub backplane (Redis pub/sub, or Kafka) that all instances subscribe to. Plus sticky sessions at the LB, heartbeats/ping-pong, and client reconnect with backoff.
**🚩** Assuming an in-memory connection dict scales horizontally.

### Q34. Deadlock — what is it, and how do you prevent it?

**Want:** Circular wait between locks. Prevention: **consistent global lock ordering** (the standard fix), or `acquire(timeout=)` + release + retry with backoff. Never hold a lock across I/O or a callback.
**🚩** Confusing it with a slow query.

---

# Section D — LLM fundamentals & prompting (Q35–48)

### Q35. What is a token? Why do you care?

**Want:** Sub-word unit (BPE). Cost and context limits are both measured in tokens. ~4 chars/token for English; **non-English and code tokenize worse** — a Hindi or JSON-heavy prompt costs more than it looks.
**🚩** "A token is a word."

### Q36. Temperature vs top_p — what do they do, and would you set both?

**Want:** Temperature reshapes the distribution (flatter = more random); top_p truncates to the smallest set of tokens with cumulative probability p. **Convention: tune one, not both.** Extraction/classification → temperature 0. Creative → higher.
**🚩** "Temperature makes it more creative" with no mechanism.
**You:** *"For the DHR field extraction we run at temperature 0 — I want the same sheet to produce the same fields every time, because a report that changes between runs is unauditable."*

### Q37. Temperature 0 — is the output deterministic?

**Probes:** Depth beyond the textbook.
**Want:** **Not guaranteed.** Batching, floating-point non-associativity on GPUs, MoE routing, and provider-side model updates all introduce variance. Closer to deterministic, not deterministic. Some providers offer a `seed` and a system fingerprint, best-effort.
**🚩** A flat "yes." This one separates the top 20%.

### Q38. Context window — what happens when you exceed it?

**Want:** Hard API error, or silent truncation depending on the client. Mitigations: chunking, summarisation, sliding window, retrieval instead of stuffing. Also: **long context ≠ good recall** — "lost in the middle," where models attend better to the start and end than the middle.
**You:** Mention lost-in-the-middle by name and I'll mark you up.

### Q39. Zero-shot vs few-shot vs chain-of-thought — when do you use each?

**Want:** Few-shot for format/style consistency; CoT for multi-step reasoning; note that CoT costs tokens and latency, and that newer reasoning models do it internally so explicit "think step by step" can be redundant or harmful.

### Q40. What actually goes in a system prompt vs a user prompt?

**Want:** System = role, constraints, output format, tone, **safety rules** — stable across turns. User = the request/data. **Critically: retrieved documents and user files are *data*, not instructions** — keep them clearly delimited.
**🚩** Putting everything in one blob.

### Q41. How do you get reliable JSON out of an LLM?

**Probes:** ⚠️ Your resume claims "structured JSON validation (schema checks, retry, fallback)" — I *will* ask.
**Want, in order of strength:**
1. Provider **structured output / JSON schema mode** (constrained decoding — can't emit invalid JSON)
2. Function/tool calling with a typed schema
3. Prompt + **Pydantic validation + repair retry** (feed the validation error back)
4. Last resort: regex-extract the JSON block
Plus: a fallback path when all retries fail, and logging the failures.
**You:** Describe Pitcher's actual chain — schema check → retry → fallback — and say what the fallback *did*.

### Q42. What's a hallucination, and how do you reduce it?

**Want:** Fluent, confident, wrong. Reductions: ground in retrieved context, **instruct abstention** ("if the context doesn't contain the answer, say so"), require citations, lower temperature, validate against a schema/source, self-consistency for high-stakes. Note: you reduce it, you don't eliminate it.
**🚩** "Better prompts fix it."
**You:** Tie to your resume line about grounding to reduce hallucination — but make it concrete: *"In the interview-prep platform, every claim in the skill-gap report had to trace to a line in the resume or JD; if it couldn't, we dropped it."*

### Q43. What is prompt injection, and how do you defend against it?

**Probes:** ⚠️ Security. Rare at this band — big differentiator.
**Want:** Untrusted input containing instructions the model obeys. **Direct** (user types it) vs **indirect** (poisoned document that your RAG retrieves — *this is the one that matters for you*). Defences: treat retrieved content as data with clear delimiters, never put secrets in the prompt, least-privilege tools with allowlists, human confirmation for destructive actions, output filtering. No prompt-level defence is complete — architecture is the defence.
**You:** *"For the hospital RAG this is a real risk — if someone puts 'ignore previous instructions' in an Excel cell, that text goes into my prompt. That's why the extraction is schema-constrained: the model can only fill declared fields, so injected instructions have nowhere to land."*

### Q44. When would you fine-tune instead of using RAG?

**Want:** **RAG for knowledge, fine-tuning for behaviour/format/style.** Fine-tune when: consistent output format, a domain tone, a narrow task where a small cheap model can replace a large one, or latency/cost pressure. Don't fine-tune to teach facts that change. Also: RAG first, always — it's cheaper and updatable.
**🚩** "Fine-tune to add company knowledge." Common and wrong.

### Q45. What's LoRA / PEFT, at a high level?

**Want:** Train small low-rank adapter matrices instead of all weights — far less memory, swappable adapters, near-full-FT quality for many tasks. QLoRA adds quantisation of the base model.
**🚩** Bluffing depth here. *"I understand it conceptually but haven't trained one"* is a perfectly good answer — take it if it's true.

### Q46. Your LLM feature's p95 latency is 8 seconds. Users complain. What do you do?

**Probes:** Debugging method under vague symptoms.
**Want, in order:**
1. **Measure first** — break down the 8s: retrieval? embedding? model TTFT? generation? network?
2. Then the levers: **stream** (fixes perceived latency immediately), smaller/faster model, shorter output (`max_tokens`), fewer/shorter retrieved chunks, prompt caching, parallelise independent steps, cache whole responses.
**🚩** Jumping straight to "use a smaller model."
**You:** *"First thing I'd ship is streaming — it doesn't reduce total time but time-to-first-token is what users actually feel. Then I'd look at whether we're over-retrieving."*

### Q47. How do you cut LLM cost by half without wrecking quality?

**Want:** Prompt caching for stable prefixes; response caching with TTL (**you did this — 24h TTL in the interview-prep platform**); route easy requests to a cheap model and hard ones to the expensive one; shorten prompts (few-shot examples are expensive); cap `max_tokens`; batch where latency allows.
**You:** Lead with your own Redis TTL cache — it's a real, measured example. Then say what cache-hit rate you saw, or admit you didn't measure it.

### Q48. How do you pick a model for a new feature?

**Want:** Build a small **eval set from real data first**, then compare candidates on quality/latency/cost, not on leaderboards. Consider data residency, rate limits, provider lock-in, and structured-output support. Re-evaluate periodically — models change under you.
**🚩** "I'd use whichever is best on the leaderboard."
> ⚠️ Model names, context limits, and pricing move fast. Before an interview, check the current docs for whichever provider the company uses — don't quote figures from memory.

---

# Section E — RAG deep dive (Q49–68)

***This is the section that decides your offer.*** Two RAG systems on your resume
means I get to go three levels deep. Prepare this section hardest.

### Q49. Explain RAG to a non-technical stakeholder in 30 seconds.

**Want:** "The model doesn't know our internal documents. So before answering, we search our documents for the relevant passages and give them to the model, then it answers using only those — with citations."
**🚩** Jargon soup.

### Q50. Draw the full RAG pipeline, ingestion through response.

**Want:** Load → clean → **chunk** → embed → store (vector + metadata) → *query time*: rewrite query → embed → retrieve (dense + sparse) → **rerank** → assemble context → prompt with grounding rules → generate → cite → **log for eval**.
**🚩** Missing reranking or the eval loop. That's the "I did a tutorial" tell.

### Q51. What's an embedding? What does cosine similarity actually measure?

**Want:** Dense vector where geometric closeness ≈ semantic relatedness. Cosine = angle, ignores magnitude. **Key nuance: it measures *relatedness*, not *answerhood*** — "How do I cancel my subscription?" is highly similar to "How do I renew my subscription?" and one is useless.
**🚩** "It measures how similar the meaning is" with no awareness of the failure.

### Q52. How did you chunk documents, and why that way?

**Probes:** ⚠️ **The single most common source of bad RAG.**
**Want:** Strategy tied to document structure — recursive character splitting respecting paragraph/section boundaries, or structure-aware for tables/headers. A size (256–1024 tokens is the usual range) with **10–20% overlap** so an answer split across a boundary survives. And critically: **you tuned it by testing, not by copying a default.**
**🚩** "1000 characters with 200 overlap" and no reason. That's the LangChain default and I'll know.
**You:** For the DHR agent — Excel is *tabular*, so naive text chunking is wrong. Say that: *"Splitting a spreadsheet by character count destroys row integrity. We chunked by logical record — a row or a section — and kept the header in every chunk so the model knew what the columns meant."* **That answer alone is worth a band.**

### Q53. A user asks a question, retrieval returns garbage. Debug it.

**Probes:** Systematic debugging of a black box.
**Want, in order:**
1. Is the answer even **in the corpus**? (Half of all "RAG bugs" are missing data.)
2. Is it in the **index** — did ingestion silently drop it?
3. Does it survive **chunking** — is the answer split across a boundary?
4. Is the **embedding model** wrong for the domain (jargon, acronyms, other languages)?
5. Is it a **query/document mismatch** — short question vs long document (fix: HyDE, query rewriting)?
6. Is it **ranked but below k** — check top-50 before blaming retrieval.
**🚩** Immediately blaming the LLM. The LLM is almost never the problem.

### Q54. Vector search vs keyword search — which is better?

**Want:** Neither. **Hybrid.** Dense handles paraphrase and semantics; sparse/BM25 nails exact terms — product codes, error codes, names, acronyms — where dense embeddings are famously weak. Combine with **Reciprocal Rank Fusion** or weighted scores.
**You:** For the hospital domain this is a strong concrete point: *"Instrument codes and hospital site IDs are exact strings — dense retrieval is bad at those. That's exactly where BM25 earns its place."*

### Q55. What's a reranker, and why bother if you already have similarity scores?

**Want:** Retrieval is a **bi-encoder** — question and document embedded *separately*, so it's fast but approximate. A **cross-encoder reranker** sees the query and document *together* and scores actual relevance — much better, much slower. So: retrieve top 50 cheaply, rerank to top 5, send those. Usually the single biggest quality jump per unit of effort.
**🚩** Never having heard of reranking. At this band it's a real gap.

### Q56. What's the tradeoff in choosing `k` (number of retrieved chunks)?

**Want:** Too low → missing context, model can't answer. Too high → noise, cost, latency, and **lost-in-the-middle** degradation. Tune empirically against an eval set. Reranking lets you retrieve wide and send narrow.

### Q57. How do you handle a question that needs information from multiple documents?

**Want:** Single-shot retrieval often fails. Options: **query decomposition** (split into sub-questions, retrieve for each), multi-hop/iterative retrieval, higher k with reranking, or an agentic loop that decides it needs to search again.
**🚩** Assuming one retrieval always suffices.

### Q58. HNSW vs IVFFlat — pick one for pgvector and defend it.

**Probes:** ⚠️ You list PostgreSQL heavily. I'll go here.
**Want:** **HNSW** — graph-based, best recall/latency, no training step, but higher memory and slower build. **IVFFlat** — clusters vectors into lists, needs training data present before indexing, tune `lists` and `probes`, lower memory, faster build, generally worse recall. Default to HNSW unless memory-constrained. Both are **approximate** — you trade recall for speed.
**🚩** Not knowing ANN indexes are approximate.

### Q59. Why did you use pgvector instead of a dedicated vector DB?

**Want:** **One database.** Transactional consistency between your rows and your vectors, one backup story, one ops burden, and you can filter on SQL metadata *and* vector-search in one query. Move to a dedicated store when scale, sharding, or specialised features demand it. Naming the switch condition is what I want.
**🚩** "Because it was easy." True, but say the operational reason.

### Q60. How did you evaluate your RAG system?

**Probes:** ⚠️⚠️ **THE band-defining question.** Most candidates have no answer. If you have one, you jump.
**Want:**
- A **golden set** — 50–200 real questions with known-correct answers, built with domain experts (for you: the hospital ops team).
- **Retrieval metrics** separately from generation: recall@k, MRR, hit rate. *Fixing retrieval and fixing generation are different jobs.*
- **Generation metrics:** faithfulness (is it supported by the context?), answer relevance, context precision/recall — the RAGAS framing.
- **LLM-as-judge** for scale, calibrated against human labels on a sample.
- Run it in **CI** so a prompt or chunking change can't silently regress.
- **Production signals:** thumbs down, edit-rate on auto-filled fields, escalation rate.
**🚩** "We tested it manually and it looked good."
**You (if you didn't do formal evals — say so, then show you know how):** *"Honestly, at SimplifyAI we didn't have a formal eval harness — we relied on manual spot-checks and user feedback, and I think that was our biggest weakness. If I were starting it again the first thing I'd build is a golden set of 100 real questions and a CI job measuring recall@k and faithfulness, because without it every prompt change is a guess."*
> **That answer is stronger than a fabricated one.** It shows you know what good looks like and you can critique your own work. This is exactly the honest-calibration signal I score at ★★★.

### Q61. Your RAG answers are wrong 20% of the time. Where do you look?

**Want:** **Split the failure first.** Retrieval failure or generation failure? Check: was the right chunk retrieved? If yes → the model ignored it or the prompt is weak (generation problem: grounding instructions, context ordering, model choice). If no → retrieval problem (chunking, embedding, hybrid, reranking). *Never fix both at once.*
**🚩** Changing the prompt and the chunking together, then not knowing which helped.

### Q62. How do you handle "I don't know"?

**Want:** Explicit instruction to abstain, a **similarity/rerank score threshold** below which you don't even call the LLM, and a fallback path (escalate to a human, offer search results). In a hospital context, a confident wrong answer is far worse than an abstention — say that.

### Q63. How do you keep the index fresh when source documents change?

**Want:** Content-hash per chunk to detect changes; delete-and-reinsert affected chunks (not full reindex); soft-delete for removed docs; versioned document ids; a background job or CDC/webhook trigger; handle the reindex-while-serving case.
**🚩** "Rebuild the whole index nightly" with no awareness of cost or staleness window.

### Q64. How do you do access control in RAG — user A must not retrieve user B's documents?

**Probes:** ⚠️ **Huge in healthcare and HR — both your domains.** Frequently missed.
**Want:** **Filter at retrieval time, in the query — never post-filter after the LLM sees it.** Metadata on every chunk (tenant id, site id, role), pre-filtered vector search (pgvector's advantage: a SQL `WHERE` in the same query), and per-tenant namespaces if the store supports them. And: **the LLM must never see a document the user can't see**, because it will leak it in the summary even if you filter the citation.
**You:** Frame it with your own domain: *"For 10+ hospital sites this is the thing that would get us in real trouble — site A's data must never surface in site B's report. It's a pre-filter on the retrieval query, not a post-filter."*

### Q65. How do you cite sources, and what makes citation hard?

**Want:** Return chunk ids/metadata alongside the answer; ask the model to reference chunk ids inline; then **verify** the cited chunk actually supports the claim (models cite the wrong chunk confidently). Map chunk → page/section for the UI.

### Q66. What's HyDE, and when would you use it?

**Want:** Hypothetical Document Embeddings — have the LLM write a *fake answer* to the question, embed **that**, and retrieve with it. Works because a hypothetical answer is more similar to real answer-documents than a short question is. Costs an extra LLM call. Use when queries are short and documents are long.
**Bonus:** query rewriting, multi-query expansion, step-back prompting as related techniques.

### Q67. How would you support Hindi or mixed-language queries in your hospital system?

**Probes:** India-specific, practical, and rarely prepared for.
**Want:** A **multilingual embedding model** (monolingual English embeddings fail badly here); test retrieval cross-lingually (Hindi query → English document); tokenization costs more for Indic scripts; consider translating the query at retrieval time; evaluate separately per language.
**🚩** Assuming an English embedding model just works.

### Q68. Design a RAG system over 10 million documents. What changes vs your 10,000?

**Probes:** Scale thinking.
**Want:** Ingestion becomes a distributed pipeline (batching, backpressure, resumability); index build time and memory dominate → sharding/partitioning, possibly a dedicated vector store; ANN parameter tuning matters much more; **two-stage retrieval becomes mandatory** (cheap wide recall → expensive rerank); caching hot queries; metadata pre-filtering to shrink the search space; monitoring recall drift over time.
**🚩** "Same thing, bigger machine."

---

# Section F — Agents, tool-calling, LangGraph (Q69–78)

### Q69. What makes something an "agent" rather than a prompt chain?

**Want:** **The LLM decides the control flow** — which tool, whether to loop, when to stop. A chain has flow fixed by you. Agents are more capable and much less predictable; prefer a chain when the flow is known.
**🚩** Calling every LLM call an agent.

### Q70. Explain function/tool calling mechanically. What actually happens?

**Probes:** ⚠️ Your resume claims tool-calling. Must be crisp.
**Want:** You send tool **schemas** with the request → the model returns a structured **call request** (name + JSON args), it does *not* execute anything → **your code executes it** → you send the result back as a tool message → the model produces the final answer. Multi-turn loop.
**🚩** Thinking the model runs the function. This is the classic misconception and an instant flag.
**You:** *"In Pitcher the model calls `go_to_slide(n)` — but the model never touches the UI. It emits the call, my relay validates the slide index is in range, executes it, and sends the result back. The validation matters: nothing stops a model from asking for slide 47 of a 12-slide deck."*

### Q71. How do you write a good tool description?

**Want:** The description **is** the prompt for that tool — clear purpose, when to use *and when not to*, typed parameters with constraints, examples. Vague descriptions are the #1 cause of wrong tool selection.
**🚩** `"""does stuff with slides"""`

### Q72. Your agent loops forever calling the same tool. Fix it.

**Want:** Hard cap on iterations; detect repeated identical calls; return *useful* error messages so the model can correct rather than retry blindly; check the tool description is ambiguous; consider a state machine instead of a free agent; timeout + fallback to a human.
**🚩** "Increase max iterations."

### Q73. What's LangGraph, and why use it over a plain agent loop?

**Probes:** ⚠️ Listed on your resume — I'll check it's real.
**Want:** Graph of nodes over an explicit shared **state**, with conditional edges and **cycles**. Gives you: inspectable state, checkpointing/persistence, human-in-the-loop interrupts, resume-after-failure, and controllability that a free-form ReAct loop lacks. Use it when the workflow has structure you want to enforce.
**🚩** "It's LangChain but newer." If you haven't actually used it, **say so** — a bluff here is easy to expose with one follow-up.

### Q74. What are your honest reservations about LangChain?

**Probes:** Independent judgement.
**Want:** Abstraction depth makes debugging hard; hidden prompts you didn't write; version churn; often simpler to call the provider SDK directly for production paths. But: good for prototyping and for standard integrations.
**🚩** Pure fanboy or pure hater. I want a *considered* position.

### Q75. How do you manage conversation memory in a long chat?

**Want:** Sliding window of recent turns; running summarisation of older turns; retrieval over past conversation ("memory as RAG"); store facts extracted into structured memory. Tradeoff: summarisation loses detail, full history costs tokens and hits lost-in-the-middle.

### Q76. How do you test an agent, given it's non-deterministic?

**Want:** Test the **components** deterministically (tools, parsers, validators) with normal unit tests; test the agent on a **fixed scenario set** with assertions on *outcomes and invariants*, not exact text; record/replay LLM responses (VCR-style) for CI; assert "the right tool was called with the right args"; track a success rate over the scenario set rather than pass/fail per run.
**🚩** "You can't really test it."

### Q77. When would you NOT use an agent?

**Want:** When the flow is deterministic, when latency matters (each hop is a round trip), when the cost of a wrong action is high, when reliability must be near-100%. A state machine or plain chain is better. Agent flexibility is a liability in a hospital workflow.
**You:** This is a maturity signal — I want to hear you say "usually, don't."

### Q78. An agent needs to delete records. How do you make that safe?

**Want:** Least privilege (soft-delete tool, not `DROP`), human confirmation for destructive actions, allowlisted scopes, dry-run/preview mode, full audit log, idempotency, and rate limits. Combine with the prompt-injection answer from Q43 — a poisoned document must not be able to trigger a delete.

---

# Section G — Realtime voice & WebSockets (Q79–85)

*Pitcher deep dive. This project is your differentiator — own it.*

### Q79. Walk me through Pitcher's architecture.

**Want:** Browser ↔ FastAPI relay ↔ realtime model over WebSocket; audio streamed as 24kHz PCM both ways; the model tool-calls `go_to_slide(n)` which the relay validates and forwards to the UI; slide generation as a separate structured-output step. Explain *why a relay* — the API key must never reach the browser.
**🚩** Not knowing why the relay exists. That's the security answer.

### Q80. Why WebSocket and not WebRTC for audio?

**Probes:** Did you choose, or did you copy?
**Want:** WebSocket = simpler, TCP, works everywhere, fine for a single-user demo — but TCP head-of-line blocking hurts under packet loss. WebRTC = UDP, jitter buffer, echo cancellation, built for real-time audio, and what you'd move to for production or multi-party. Name the tradeoff and the switch condition.
**🚩** "WebSocket because that's what the docs used." (Even if true, add what you'd change and why.)

### Q81. Explain barge-in. Why is it hard?

**Probes:** ⚠️ Your hardest technical claim. Nail it.
**Want:** The user interrupts while the AI is speaking. Hard because: (a) you must **detect** speech onset fast (VAD) while your own audio is playing, (b) you must **stop playback immediately** — and audio already buffered client-side will keep playing unless you **flush the buffer**, (c) you must **truncate the model's server-side context** to what was *actually heard*, or the model believes it said things the user never heard, and every subsequent turn is misaligned.
**You:** That third point is the one that separates "I read the docs" from "I built it." Lead with it.

### Q82. Server-side VAD vs client-side — what did you choose and why?

**Want:** Server-side = provider handles turn detection, less client code, but a round trip of latency before interruption registers. Client-side = faster local reaction, more code, risk of false triggers from the AI's own audio (needs echo cancellation). Your resume says server-side VAD **with client-side buffer flushing** — that's a hybrid, and you should explain it as a deliberate split: *detection* on the server, *reaction* on the client.

### Q83. What's your latency budget for a voice agent, and where does it go?

**Want:** Conversation feels natural under roughly 500–800ms response onset. Budget: network RTT + VAD turn-detection delay + model time-to-first-token + TTS onset + client buffer. **Streaming is mandatory** — you play the first audio chunk while the rest generates.
**🚩** No sense of the number.

### Q84. The WebSocket drops mid-presentation. What happens?

**Want:** Detect via heartbeat/ping-pong; client reconnects with exponential backoff; **session state must live server-side** (current slide, conversation context) so reconnect resumes rather than restarts; buffer or drop audio explicitly; tell the user. Be honest if you didn't build all of it: *"I handled reconnect but not full session resume — that's the first thing I'd add."*

### Q85. How would you make Pitcher multi-tenant and production-ready?

**Want:** Auth per session; per-user rate limits and **hard cost caps** (realtime audio models are expensive per minute); session state in Redis, not memory; horizontal scaling with sticky sessions or a shared backplane (ties to Q33); observability on cost-per-session; graceful degradation to text when audio fails.

---

# Section H — Data, caching, scale (Q86–92)

### Q86. Your query is slow. Walk me through diagnosing it.

**Probes:** ⚠️ You claim 35% and 73% improvements. This is where I verify.
**Want:** `EXPLAIN ANALYZE` first. Read for: sequential scan on a large table, bad row estimates, nested loop over many rows, sort spilling to disk. Then: is there an index? is it *usable* (leading column, no function wrapping the column)? Is it an N+1 from the ORM? Then measure again.
**🚩** "I added an index" with no diagnosis step.
**You:** Give the *actual* story from SimplifyAI, with the before/after numbers.

### Q87. When does an index hurt?

**Want:** Every write must update it; bloats storage; low-cardinality columns rarely benefit; too many indexes slow inserts. The planner may ignore one if it estimates a large fraction of rows will match.

### Q88. Composite index on `(a, b)` — does a query filtering only on `b` use it?

**Want:** **No** (barring index-only scan tricks) — leftmost-prefix rule. Order columns by selectivity and by query pattern.
**🚩** Guessing yes.

### Q89. Partitioning vs sharding — define both, and tell me which you actually did.

**Probes:** ⚠️ **The landmine.** Directly on your resume.
**Want:** **Partitioning** = splitting one table within one database (by range/list/hash) — the DB routes queries, one server. **Sharding** = splitting data across *separate databases/servers* — needs a shard key, app or middleware routing, and cross-shard joins become painful. Then: state clearly which you did.
**You:** If it was partitioning, correct the resume wording *proactively* (see landmine #1). Volunteering the correction is a trust signal; getting caught is a rejection signal.

### Q90. Redis cache — what eviction policy, and what's your invalidation strategy?

**Probes:** Your 24h TTL claim.
**Want:** `allkeys-lru` for a pure cache, `noeviction` if it's a queue/broker (evicting Celery tasks would be catastrophic — this distinction matters given you ran Celery on Redis). Invalidation: TTL, explicit delete on write, versioned keys. Name the two hard problems: **stale data** and **cache stampede**.

### Q91. 10,000 users hit an uncached endpoint simultaneously when the cache expires. What happens?

**Want:** **Cache stampede** — all miss, all hit the LLM/DB at once. Fixes: **single-flight** (one caller computes, the rest wait on a per-key lock), stale-while-revalidate, jittered TTLs so keys don't all expire together, probabilistic early refresh.
**🚩** Never having heard of it. (You've now implemented this — problem 4 in your machine_coding repo. Use that.)

### Q92. What's your caching key for an LLM response, and what breaks it?

**Want:** Hash of (model + prompt + params + retrieved context + user scope). Breaks when: temperature > 0 makes caching semantically wrong; the prompt template changes (**version it into the key**); user-specific context leaks across users if scope isn't in the key — a **security** bug, not just a correctness one.
**You:** That last point elevates the whole answer.

---

# Section I — Evals, cost, safety, production (Q93–98)

### Q93. How do you monitor an LLM feature in production?

**Want:** Log every request/response with a trace id (LangSmith/Langfuse/Phoenix or your own tables); track latency p50/p95/p99, token counts, **cost per request**, error and retry rates, tool-call success rates; user feedback (thumbs, edit rate); sample outputs for offline scoring; alert on cost and latency anomalies.
**🚩** Only application logs, no LLM-specific observability.

### Q94. How do you detect quality regression when the provider silently updates the model?

**Probes:** ⚠️ Rare and excellent. Big differentiator.
**Want:** Pin model versions where the provider allows it; run the golden eval set on a schedule (not just on your own deploys); track score over time; canary a new version against the old before switching.
**🚩** Assuming the model is a fixed dependency.

### Q95. What PII/compliance concerns apply to your hospital system?

**Probes:** ⚠️ Directly relevant to your domain — and to any Indian health/HR product.
**Want:** Patient data must not leak into third-party model providers without a data agreement; check whether the provider trains on your data (usually off for enterprise/API tiers, but *verify*); PII detection and redaction before the prompt; data residency (India's DPDP Act, HIPAA if US-facing); audit logs; retention limits; consider self-hosted models for the most sensitive paths.
**🚩** Never having thought about it. In healthcare that's disqualifying.

### Q96. Set a monthly LLM budget for a feature and enforce it. How?

**Want:** Estimate tokens/request × requests/month × price → forecast. Enforce: per-user and per-org rate limits, hard caps with graceful degradation, token ceilings per request, cheap-model routing, caching, and alerting at 50/80/100% of budget. Track cost per *feature*, not just total.

### Q97. Your LLM provider has a 3-hour outage. What happens to your product?

**Want:** Multi-provider abstraction behind your own interface; failover to a secondary; circuit breaker so you fail fast instead of piling up retries; queue jobs for later where async is acceptable; degrade gracefully (cached/templated response, or a clear "AI features unavailable" state) rather than 500ing.
**🚩** "We'd be down." Even naming the *plan* you'd build scores.

### Q98. Tell me about a bug in an AI system that took you a long time to find.

**Probes:** ⚠️ **Most revealing question in the interview.** I learn more here than from ten definitions.
**Want:** Specific symptom → what you thought → how you narrowed it → the actual cause → the fix → what you changed *systemically* so it can't recur.
**🚩** A generic answer, or one where you were never wrong along the way.
**Good candidates from your work:** chunking destroying Excel row integrity; a Celery task silently retrying and double-charging LLM calls; barge-in leaving the model's context out of sync with what the user actually heard; a cache key missing user scope.
**Prepare ONE of these in detail.** Rehearse it out loud. It's the most likely question in this document to decide your offer.

---

# Section J — Live coding & system design (Q99–100)

### Q99. Live coding (20 min)

I'd give you **one** of these. All are RAG/LLM-flavoured, all are runnable, none need a library.

**(a) Token-budget context packer.**
Given chunks with relevance scores and token counts, and a budget, select chunks maximising total score within budget. Then: *"put the highest-scoring chunk last — why?"* (**lost in the middle**.)

**(b) Chunker with overlap.**
Split text into ~N-token chunks with M overlap, without breaking sentences. Edge cases: text shorter than N, a single sentence longer than N, overlap ≥ N.

**(c) Sliding-window rate limiter for an LLM API.**
Per-user, thread-safe. *(You've built exactly this — problem 1 in your machine_coding repo.)*

**(d) Retry with exponential backoff + jitter as a decorator.**
Then: *"why jitter?"*

**(e) In-memory response cache with TTL + single-flight.**
20 concurrent identical requests must trigger exactly one LLM call. *(Problem 4 in your repo.)*

**What I score:** clarifying questions first; a working simple version before optimising; edge cases named out loud; **you write at least one test unprompted**; you talk while you type.
**🚩** Silent typing. Optimising before it works. No edge cases.

### Q100. System design (20 min) — "Design an AI assistant that answers questions over a company's internal documents. 5,000 employees, 2 million documents, strict per-user access control."

**Probes:** Everything above, integrated.

**Want, roughly in this order:**

1. **Clarify first** (2–3 min): document types? update frequency? latency expectation? accuracy bar? budget? data residency? *Not clarifying is the most common failure.*
2. **Ingestion:** connectors → parse → structure-aware chunk → embed (batched, resumable) → store with **ACL metadata on every chunk**.
3. **Retrieval:** hybrid (dense + BM25) → **ACL pre-filter in the query** → rerank top-50 → top-5.
4. **Generation:** grounding prompt, citations, abstention threshold, streaming.
5. **Access control:** emphasise **pre-filter, never post-filter** (Q64). At 5,000 employees this is the requirement most likely to end the project if you get it wrong.
6. **Freshness:** incremental reindex on change, content hashing, soft deletes.
7. **Evals:** golden set, retrieval and generation measured separately, CI gate, production feedback loop.
8. **Ops:** caching (per-user scope in the key!), cost caps, observability, provider failover.
9. **Tradeoffs you'd revisit:** pgvector now → dedicated store at what threshold; agent vs fixed chain; self-hosted model if compliance demands it.

**🚩** Drawing boxes without naming the failure modes. Forgetting ACLs. No eval story.
**The thing that would make me say yes:** you volunteer *"the two things most likely to kill this project are access control leaks and having no way to measure quality"* — before I ask.

---

# Questions YOU should ask me

Asking nothing reads as low interest. Ask 3–4. These signal seniority:

1. "How do you currently evaluate your LLM features — is there an eval set, or is it manual review?"
2. "What's the split between building new AI features and maintaining existing pipelines?"
3. "What's your monthly LLM spend roughly, and is cost a live constraint on design decisions?"
4. "Is the AI work core product or a feature layer? Who owns the roadmap?"
5. "What does the first 90 days look like — is there a specific problem you'd want me on?"
6. "How big is the engineering team, and would I be the only person on the AI side?"

**Avoid** asking only about WFH/leave/timings in the technical round. Save those for HR.

---

# On the ₹12 LPA number

- **Have a number ready.** When asked expected CTC, say a **range with 12 at the bottom**: *"I'm looking at 12–15 depending on the overall package and scope."* Never say "whatever you offer."
- **Know your current CTC and be honest about it.** It will be verified.
- **Your leverage:** production GenAI experience at ~1 YoE is genuinely uncommon. Most applicants at this band have tutorials and course projects. You have two shipped RAG systems and a real-time voice agent. **Say that clearly** — not arrogantly, factually.
- **Your weakness:** short tenures and a 2026 graduation date. Counter with depth on Q98 (the debugging story) and Q60 (evals) — those read as seniority regardless of years.
- If they offer 10: *"I'm keen on the role. Is there flexibility to get to 12? I'd also consider a 6-month review tied to specific deliverables."* Ask once, politely, then decide.

---

# The night before

**Rehearse out loud** — 6 things only:

1. Your 2-minute intro (Q1)
2. The **partitioning vs sharding** correction (Q89 / landmine 1)
3. Your **73% / 35%** stories with baseline, method, and change (Q86)
4. The **barge-in** explanation, including context truncation (Q81)
5. Your **eval** answer — including the honest "we didn't have one, here's what I'd build" (Q60)
6. Your **hardest bug** story, start to finish (Q98)

**Skim:** Q24 (`def` vs `async def`), Q27 (Celery task loss), Q41 (structured output), Q55 (rerankers), Q64 (RAG access control).

**Two rules for the room:**

- **Never bluff.** *"I haven't used that — here's how I'd approach it"* costs you nothing at this band. A confident wrong answer costs you the offer, because now I doubt everything else you said.
- **Talk while you think.** Silence gets read as not knowing.

You have real production GenAI experience at a stage where most candidates don't. Go in knowing that.
