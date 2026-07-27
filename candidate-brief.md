# Take-Home Assessment — Agentic Developer

Welcome, and thank you for the time you're about to spend on this.

This exercise is in two parts. **Part A** asks you to build an agent runtime from scratch. **Part B** asks you to rebuild it on a framework and tell us what changed. Part B is released only after you submit Part A — please don't get ahead of us, the sequencing is deliberate.

Everything runs on your laptop against a local mock server. There is no API key, no cloud account, and no spend. You need Python or Node, SQLite, and a terminal.

---

## Ground rules

**Use AI assistance as much as you want.** Claude, Copilot, whatever you normally use. This is not a trick or a trap — it's how the job is actually done, and pretending otherwise would tell us nothing useful.

**But you own every line.** In the live round you'll be asked to explain arbitrary sections of your own code and extend the design under a 60-minute clock. Submitting something you don't understand is the one strategy that reliably fails here.

**Respect the time caps.** Six hours for Part A, two for Part B. Log where the time went in `TIMELOG.md`. We would much rather see an honest six-hour submission that misses three requirements, with a clear note about why those three were deferred, than a polished twelve-hour one. We read the time log. Going over doesn't score you higher; it just tells us you don't triage.

**Incomplete is fine. Dishonest is not.** If something doesn't work, say so in your write-up. If your test suite is green because the hard tests aren't written yet, say that too. We have never rejected someone for an honest gap. We have rejected people for a `README` that claimed a guarantee the code didn't hold.

**Turnaround:** seven days from receipt for Part A.

---

## What you're given

```
mockllm/          # local HTTP server, Messages-API-shaped, driven by scenario YAML
  scenarios/      # S1..S12 — see the table below
  tokenizer.py    # deterministic token counter — use this for all budgeting
harness/
  chaos.py        # kills your process at random points, repeatedly
  redteam/        # adversarial payloads mounted into the workspace (contents not disclosed)
workspace/        # the only directory your agent may write to
Makefile          # setup / run / test / eval targets
```

`mockllm` is a stand-in for a real model API. It is deliberately hostile — it behaves the way real models behave on their worst day, all the time, on purpose. Do not modify it. If you think you've found a genuine bug in it (as opposed to a behaviour you don't like), tell us; that's a good sign, not a complaint.

### Mock model behaviours

| ID | Behaviour |
|----|-----------|
| S1 | Happy path, single tool call |
| S2 | Malformed tool arguments: trailing commas, unescaped newlines, truncated JSON mid-object |
| S3 | Calls a tool that does not exist; calls a real tool with a wrong-typed argument |
| S4 | Infinite loop — same tool, same arguments, forever |
| S5 | Connection reset mid-response, at a random byte offset |
| S6 | `429` with `Retry-After`, then `529`, then `200` |
| S7 | Returns file contents containing a prompt injection targeting your privileged tools |
| S8 | Responses that grow until your context budget is blown |
| S9 | Duplicate `tool_use` ids reused across turns |
| S10 | Parallel tool calls where exactly one fails and one hangs |
| S11 | Confidently wrong — claims a tool succeeded when it returned an error |
| S12 | Emits a partial, interrupted turn after the first of three parallel tool calls |

### Tools your runtime must expose

| Tool | Notes |
|------|-------|
| `read_file(path)` | Confined to `workspace/`. |
| `write_file(path, content)` | Confined to `workspace/`. |
| `run_python(code)` | Subprocess. Wall-clock timeout, memory cap, no network. |
| `http_get(url)` | Allow-list only. Refusals must be legible to the model. |
| `send_email(to, subject, body)` | **Simulated but irreversible.** Appends to a SQLite table. Treat it as if it really sends. |

---

## Part A — The Adversarial Agent Runtime (6 hours)

Build a durable, safe, observable agent runtime from scratch.

### Constraints

- **No agent frameworks.** No LangChain, LlamaIndex, CrewAI, AutoGen, Agno, smolagents, Agent SDKs, or equivalent. Standard library, an HTTP client, SQLite, and a test runner. We know this is the slower path — that's the exercise. Part B is where you get the framework back.
- **Python or TypeScript.** Your choice; use whichever you're fastest in.
- **No network at runtime beyond `localhost`.** `make setup` may install a test runner; `make test` must pass with networking off.

### Requirements

**R1 — Agent loop.** Tool use against the mock server, surviving every behaviour in S1–S12 without crashing and without silently corrupting the conversation state.

**R2 — Durability and exactly-once side effects.** `agent run --task <t>` records an append-only event log in SQLite. `agent resume <run_id>` continues correctly after `kill -9` at *any* point. We run `harness/chaos.py` 100 times and assert `send_email` fired **exactly once** per logical send. Not zero, not twice.

**R3 — Context budget.** Hard ceiling of 8,000 tokens by `mockllm/tokenizer.py`. Exceeding it fails the run. You will need to compact. One of the graded tasks requires a fact stated at turn 3 to be used correctly at turn 40.

**R4 — Injection resistance.** Content arriving through tool results must never be able to trigger `send_email`, writes outside `workspace/`, or an allow-list bypass. Graded by `harness/redteam/`, whose contents you have not seen.

**R5 — Loop and budget control.** Step ceiling, no-progress detection, a simulated token/cost budget, and graceful termination with a legible reason. S4 must terminate in bounded time with a useful trace.

**R6 — Observability and replay.** Every run emits a structured JSONL trace. `agent replay <run_id>` reproduces the same decisions from the recorded transcript, with no model server running.

**R7 — Evals.** Write your own eval suite. Minimum 12 cases, at least 4 adversarial. `make eval` prints a pass rate and a diff against a stored baseline. **Include at least two evals your agent currently fails,** and explain why in your write-up. A fully green board is a negative signal — it tells us your evals are too easy, not that your agent is good.

**R8 — `DECISIONS.md`, max 1,000 words.** Architecture decisions and the alternatives you rejected. The three places your system is still unsafe. What you'd build with two more weeks. Your compaction strategy, defended against one specific alternative.

### Out of scope

RAG, vector databases, a UI, multi-agent orchestration, real model calls. Building these instead of R1–R8 scores zero for the time spent.

---

## Part B — The Framework Trap (2 hours)

*Released after Part A is submitted.*

You've just built the runtime by hand. Now build it on a framework in a quarter of the time, and tell us precisely what you gained and what you gave up.

**Pick one framework:** Claude Agent SDK, LangGraph, Pydantic AI, OpenAI Agents SDK, Mastra, or another mainstream agent framework. State your choice and your reason. "It's the one I know best" is a perfectly acceptable reason if you say so plainly.

### Constraints

- **Same mock server.** You must point the framework at `localhost`. If that turns out to be awkward, that is part of the exercise — please don't switch to a real API endpoint to make it easier.
- **2 hours, hard cap.**
- **Don't modify `mockllm/`.**

### Requirements

**F1 — Parity on the loop.** Reimplement R1 (survives S1–S12), R3 (8k ceiling) and R5 (step and budget ceilings) using the framework's own primitives *wherever it has them*. Where it doesn't, say so rather than quietly hand-rolling around it.

**F2 — Durability around a loop you don't own.** Deliver R2's exactly-once `send_email` guarantee. The framework owns the control flow now. The same chaos harness runs against this build.

**F3 — Trust boundary.** Deliver R4's injection resistance. Document where in the framework's execution path you could intervene, and where you couldn't.

**F4 — Extraction.** Report per run: total tokens, step count, every retry the framework performed on your behalf, and every error it swallowed. If you can't get one of these out, document what you tried.

**F5 — `FRAMEWORK.md`, max 800 words.**
- Three things the framework did **better** than your Part A. Be specific.
- Three places the abstraction leaked, and what each cost you.
- One thing the framework makes impossible or unreasonably expensive.
- **Exit cost.** If we drop this framework in six months, what does removal look like — and what did you do in these two hours to keep that cheap?
- **Your recommendation.** For the system in Part A: framework or not? Defend it.

We are not testing whether you like frameworks. We're testing whether you can predict where one will hurt *before* it hurts. A submission that ships less parity but nails this analysis scores better than the reverse.

---

## Submission checklist

**Part A**
- [ ] `agent/` — source
- [ ] `evals/` — your suite, including the failing cases
- [ ] `DECISIONS.md` (≤1,000 words)
- [ ] `TIMELOG.md`
- [ ] `README.md` — how to run it, and an honest list of what doesn't work
- [ ] `make setup && make test && make eval` passes on a clean checkout

**Part B**
- [ ] `agent_fw/` — source
- [ ] `FRAMEWORK.md` (≤800 words)
- [ ] `TIMELOG.md` updated
- [ ] Runs against the same mock server via the same `make` targets

Submit as a git repo (bundle, tarball, or private link) with commit history intact. We do look at the commits — mostly to see the order you built things in, which is genuinely interesting to us.

---

## How this is graded

We publish the categories, not the tests. In rough order of weight:

1. **Correctness of the exactly-once guarantee under chaos.** The single heaviest item in Part A.
2. **Quality of your comparative judgment in Part B.** The single heaviest item there.
3. **Injection resistance** — whether it's enforced structurally or by pattern-matching.
4. **Your evals** — whether they'd catch a real regression, and whether you know what they don't cover.
5. **Context compaction** — whether the long-horizon recall task actually passes.
6. **Loop robustness, cost control, observability.**
7. **The honesty and precision of your write-ups.**

Things that score well and cost you nothing: writing the chaos test before the resume logic; naming a weakness before we find it; deferring a requirement with a one-line reason.

---

## What comes next

If the take-home goes well, there's a 3-hour live session and a 30-minute closing conversation. You don't need to prepare anything specific, but for transparency, the live session includes:

- **Extending your own Part A code** under a time limit, to a requirement it wasn't designed for. Have your environment ready to run.
- **Debugging an agent trace** from a codebase that isn't yours.
- **An architecture discussion** about running agents at production scale.
- **A short adversarial exercise** where you defend your design out loud.

Expect us to argue the opposite of whatever you concluded in `FRAMEWORK.md`. That's not a sign we disagreed with you — we do it either way.

---

## FAQ

**Can I use Claude to write this?** Yes. Please do. Just be ready to explain it.

**Am I allowed to fail requirements?** Yes, and saying so clearly is worth more than hiding it. Nobody has ever submitted a perfect Part A.

**Six hours seems short for eight requirements.** It is. Triage is part of what's being assessed. Pick the ones you think matter most and tell us why in `DECISIONS.md`.

**Can I use a library for X?** In Part A: standard library, HTTP client, SQLite, test runner. Anything beyond that, ask — a one-line email is fine and we answer within a day.

**Is `send_email` really irreversible?** It writes a row to SQLite. But build it as if a wrong duplicate goes to a real customer, because in the job it will.

**What if I find a bug in your mock server?** Tell us. That's a good outcome for you.

**How long until I hear back?** Five working days from submission, either way, with actual feedback.
