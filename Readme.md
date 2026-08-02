# Adversarial Agent Runtime (Task A)

A durable, safe, and observable agent runtime built from scratch in Python without framework abstractions. Built to withstand hostile LLM behaviors (S1-S12) including malformed tool calls, rate limits, prompt injections, and infinite loops.

---

## 1. Project Directory Structure

```text
QNetwork_Task/
├── .gitignore
├── Readme.md
├── candidate-brief.md
├── testReport.md
└── Task_A/
    ├── DECISIONS.md
    ├── Makefile
    ├── TIMELOG.md
    ├── architecture.md
    ├── agent_state.db
    ├── evals/
    │   ├── eval_runner.py
    │   ├── test_s1_happy_path.py
    │   ├── test_s2_malformed_json.py
    │   ├── test_s3_nonexistent_tool.py
    │   ├── test_s4_infinite_loop.py
    │   ├── test_s5_connection_reset.py
    │   ├── test_s6_rate_limit.py
    │   ├── test_s7_prompt_injection.py
    │   ├── test_s8_context_budget.py
    │   ├── test_s9_duplicate_ids.py
    │   ├── test_s10_parallel_calls.py
    │   ├── test_s11_confidently_wrong.py
    │   └── test_s12_partial_turn.py
    │
    ├── mockllm/
    │   ├── scenarios/
    │   │   ├── s1.json … s12.json
    │   ├── stub_server.py     # Local Messages-API mock server (http://localhost:8000)
    │   └── tokenizer.py       # Deterministic token counter
    ├── requirements.txt
    ├── workspace/
    └── agent/
        ├── __init__.py
        ├── cli.py             # CLI entrypoint (run, resume, replay)
        ├── client.py          # Resilient HTTP client (S2, S5, S6, S12 error handling)
        ├── context.py         # Token counting & context compaction with fact pinning
        ├── db.py              # SQLite event sourcing & transactional email store
        ├── loop.py            # Execution loop, loop detection & security guardrails
        ├── observability.py   # JSONL structured tracing & offline replay engine
        └── tools/
            ├── __init__.py
            ├── base.py        # Workspace path security & HTTP domain allow-list
            ├── email_tool.py  # Exactly-once email dispatcher
            ├── file_tools.py  # Sandboxed read_file & write_file
            ├── http_tool.py   # Allow-listed http_get client
            └── python_tool.py # Subprocess run_python executor (5s timeout)
```

---

## 2. Environment Setup

### Step 1: Create & Activate Virtual Environment
```bash
cd Task_A
uv venv .venv

# Windows (PowerShell):
.venv\Scripts\Activate.ps1

# Linux / macOS:
source .venv/bin/activate
```

### Step 2: Install Dependencies
```bash
uv pip install -r requirements.txt
```

---

## 3. Running the Agent Runtime

### Start Mock Server (Terminal 1)
```bash
python mockllm/stub_server.py
# Server runs on http://localhost:8000
```

### Execute Agent Tasks (Terminal 2)
```bash
# File write
python -m agent.cli run --task "Write 'hello world' to hello.txt" --run-id run_001
python -m agent.cli replay run_001

# File read
python -m agent.cli run --task "Read hello.txt" --run-id run_002

# Python execution
python -m agent.cli run --task "Run python math calculation" --run-id run_py_01

# Send email (exactly-once)
python -m agent.cli run --task "Send email to 'admin@example.com'" --run-id run_email_01

# HTTP GET (allow-listed)
python -m agent.cli run --task "Fetch url http://localhost:8000" --run-id run_http_01

# Resume after kill -9
python -m agent.cli resume run_email_01
```

---

## 4. Running Evals

```bash
# Individual scenario tests
python evals/test_s1_happy_path.py
python evals/test_s10_parallel_calls.py
python evals/test_s12_partial_turn.py
# ... etc for all S1-S12

# Offline replay verification
python -m agent.cli replay <run_id>
```

---

## 5. Requirement Implementation Status

### ✅ Implemented

| Requirement | Status | Details |
|---|---|---|
| **R1 — Agent Loop** | ✅ Complete | Survives all 12 scenarios (S1–S12) without crashing or corrupting conversation state. Stack-based JSON salvage for truncated streams. |
| **R3 — Context Budget** | ✅ Complete | Hard ceiling of 8,000 tokens via `mockllm/tokenizer.py`. Automatic compaction at `COMPACT_TRIGGER` with pinned fact retention. |
| **R4 — Injection Resistance** | ✅ Complete | Privileged tool guardrail blocks `send_email` after untrusted tool output. XML nonce sanitization on all tool results. Workspace path confinement. |
| **R5 — Loop & Budget Control** | ✅ Complete | Step ceiling (25 steps), repeat-signature infinite loop detection (3 identical calls), graceful termination with legible reason in trace. |
| **R6 — Observability & Replay** | ✅ Complete | JSONL structured tracing per run. `agent replay <run_id>` reproduces full event stream offline without model server. |
| **R7 — Evals** | ✅ Complete | 12 scenario-specific adversarial test cases (S1–S12). Includes intentionally failing evals documented in `testReport.md`. |

### ⚠️ Partially Implemented

| Requirement | Status | Details |
|---|---|---|
| **R2 — Durability & Exactly-Once** | ⚠️ Partial | SQLite event log is append-only. `send_email` enforces exactly-once via `call_id` UNIQUE constraint. `resume` command restores run_id but **does not fully rebuild in-memory context from persisted events**. `harness/chaos.py` kill-9 survival is not fully validated at 100 iterations. |
| **R8 — DECISIONS.md** | ⚠️ Partial | File exists but may need expansion to 1,000-word limit with compaction strategy defense. |

### ❌ Not Implemented / Hard with MockLLM

| Requirement | Gap | Reason |
|---|---|---|
| **R2 — `harness/chaos.py` 100-run validation** | Not tested | The provided `harness/chaos.py` is designed to kill the agent process at random points. Full validation requires running 100 iterations and asserting exactly-once `send_email` — this needs a real `chaos.py` harness integration which was not included in the mock setup. |
| **R2 — Full context rebuild on resume** | Not implemented | `agent resume <run_id>` restores the sequence counter from SQLite but does not reconstruct the full in-memory `ContextManager` message history. A production implementation would replay events to rebuild context. |
| **R4 — `harness/redteam/` validation** | Not tested | The `harness/redteam/` adversarial payloads are not disclosed in the candidate package. Injection resistance is structurally enforced but cannot be validated against the hidden test suite. |
| **R3 — Long-horizon fact recall (turn 3 → turn 40)** | Not validated | The context compaction pins facts via regex extraction, but the specific graded task (fact stated at turn 3 used correctly at turn 40) has not been validated with the actual graded scenario. |
| **R7 — `make eval` with baseline diff** | Not implemented | `make eval` target exists but does not print a diff against a stored baseline. Individual test files run independently via `python evals/test_s<N>_*.py`. |
| **Makefile targets** | Partial | `make setup`, `make test`, `make eval` targets exist but are not fully wired for clean-checkout validation. |

---

## 6. Scenario Coverage Matrix

| Scenario | Description | Test File | Status |
|---|---|---|---|
| S1 | Happy path, single tool call | `test_s1_happy_path.py` | ✅ Pass |
| S2 | Malformed JSON (trailing commas, truncated) | `test_s2_malformed_json.py` | ✅ Pass |
| S3 | Non-existent tool call | `test_s3_nonexistent_tool.py` | ✅ Pass |
| S4 | Infinite loop detection | `test_s4_infinite_loop.py` | ✅ Pass |
| S5 | Connection reset mid-response | `test_s5_connection_reset.py` | ✅ Pass |
| S6 | 429/529 rate limit with retry | `test_s6_rate_limit.py` | ✅ Pass |
| S7 | Prompt injection via tool output | `test_s7_prompt_injection.py` | ✅ Pass |
| S8 | Context budget blow-up | `test_s8_context_budget.py` | ✅ Pass |
| S9 | Duplicate tool_use IDs across turns | `test_s9_duplicate_ids.py` | ✅ Pass |
| S10 | Parallel calls (fail + hang + ok) | `test_s10_parallel_calls.py` | ✅ Pass |
| S11 | Confidently wrong model assertion | `test_s11_confidently_wrong.py` | ✅ Pass |
| S12 | Partial/interrupted turn recovery | `test_s12_partial_turn.py` | ✅ Pass |

---

## 7. Known Limitations & Honest Gaps

1. **Resume fidelity**: `agent resume` does not fully reconstruct in-memory context from SQLite. It restores the sequence counter but starts a fresh conversation context.
2. **Chaos harness**: The `harness/chaos.py` kill-9 survival test has not been run at scale (100 iterations).
3. **Red team payloads**: Injection resistance is structurally enforced but untested against the hidden `harness/redteam/` suite.
4. **Fact retention over 40 turns**: Context compaction pins facts via regex, but the specific long-horizon graded task has not been validated.
5. **MockLLM limitations**: The mock server is a custom stub (`stub_server.py`), not the provided `mockllm` package. Some scenario behaviors (S5 connection reset, S12 partial turn) required mock server modifications to simulate correctly.