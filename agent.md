# Agent Implementation Overview & Roadmap

## 1. Executive Summary

This document details the current implementation state of the **Adversarial Agent Runtime (Task A)** as specified in `candidate-brief.md`, highlighting what has been implemented so far and outlining the exact next steps required to fulfill all requirements (R1–R8).

---

## 2. Current Implementation State

### Implemented Components

1. **Tool Infrastructure (`Task_A/agent/tools/`)**
   - `base.py`: Defines workspace isolation (`safe_path` confined to `workspace/`) and HTTP domain allow-listing (`ALLOWED_DOMAINS`).
   - `file_tools.py`: Implements `read_file` and `write_file` bounded strictly inside `workspace/`.
   - `http_tool.py`: Implements `http_get` enforcing domain allow-lists and response truncation.
   - `python_tool.py`: Implements `run_python` subprocess execution with a 5-second wall-clock timeout and restricted working directory (`workspace/`).
   - `email_tool.py`: Implements `send_email` using transactional check-and-insert in SQLite to prevent duplicate dispatches.

2. **SQLite Schema & Event Sourcing (`Task_A/agent/db.py`)**
   - Prepared `event_log` table (`run_id`, `seq`, `event_type`, `payload`, `created_at`) with unique constraint `UNIQUE(run_id, seq)` for append-only event sourcing.
   - Prepared `emails` table (`run_id`, `call_id` UNIQUE, `to_address`, `subject`, `body`, `created_at`) to guarantee **exactly-once side effects** across process termination (`kill -9`).

3. **Core Agent Loop & Control (`Task_A/agent/loop.py`)**
   - Basic execution loop with step cap (`max_steps = 25`).
   - Simple infinite loop detector checking repeated tool calls with identical signatures (`sig` history check >= 3).

4. **Context Manager (`Task_A/agent/context.py`)**
   - Token counting integration using `mockllm.tokenizer.count_tokens`.
   - Naive history compaction preserving system prompt, initial user prompt, and recent 4 turns when approaching context ceiling.

5. **CLI & Observability (`Task_A/agent/cli.py`, `Task_A/agent/observability.py`)**
   - Command-line interface with `run`, `resume`, and `replay` subcommands.
   - Basic JSONL event logging for offline replay.

---

## 3. Gap Analysis vs. Candidate Brief Requirements (Task A)

| Requirement | Description | Current State | Status / Gaps |
|-------------|-------------|---------------|---------------|
| **R1 — Agent Loop** | Handle mock server scenarios S1–S12 | Partial | Lacks handling for malformed JSON args (S2), non-existent tools / wrong arg types (S3), network resets (S5), rate limits/529 (S6), parallel tool calls (S10), partial turns (S12). |
| **R2 — Durability & Exactly-Once** | `agent run` / `resume` with `harness/chaos.py` verification | Partial | Schema and dispatch exist, but replay/resume flow needs bulletproof transaction recovery under chaos killing. |
| **R3 — Context Budget** | 8,000 token ceiling with fact retention across 40 turns | Partial | Context compaction exists, but summary strategy needs enhancement to ensure turn 3 facts persist to turn 40. |
| **R4 — Injection Resistance** | Prevent prompt injections from triggering unauthorized tools/writes | Partial | Workspace path checks exist, but output sanitization and tool privilege isolation against `harness/redteam/` are pending. |
| **R5 — Loop & Budget Control** | Step ceiling, no-progress detection, token/cost budget, legible termination | Partial | Step cap and repeat detection implemented; no-progress detection and explicit token budget bounds need refinement. |
| **R6 — Observability & Replay** | Structured JSONL trace, offline replay (`agent replay`) | Implemented | JSONL tracing and replay module present; needs thorough evaluation against offline scenarios. |
| **R7 — Evals** | Minimum 12 cases, at least 4 adversarial, 2 intentionally failing | Pending | Evaluation suite under `evals/` needs full test case suite implementation and `make eval` integration. |
| **R8 — DECISIONS.md** | Max 1,000 words architecture write-up | Pending | `DECISIONS.md` created as placeholder; requires comprehensive design rationale documentation. |

---

## 4. Immediate Next Steps

1. **Robustify Mock LLM Handling (R1 & R6)**
   - Add resilient response parsing (handling malformed JSON, truncated streams, and parallel tool arrays).
   - Implement HTTP retry logic with backoff for 429/529 error codes.

2. **Harden Exactly-Once Execution & Chaos Resilience (R2)**
   - Conduct chaos test simulations using SQLite WAL transactions to ensure `send_email` executes **exactly once**.

3. **Enhance Context Compaction & Fact Retention (R3)**
   - Refine `ContextManager` to extract key key-value facts during compaction so turn-3 facts are preserved through turn 40.

4. **Build Evals & Documentation (R7 & R8)**
   - Construct 12+ eval test cases under `evals/` (including 4 adversarial & 2 failing cases).
   - Write `DECISIONS.md` documenting architecture trade-offs, security model, and compaction strategy.
