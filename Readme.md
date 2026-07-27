# 🛡️ Adversarial Agent Runtime (Part A)

A durable, safe, and observable AI agent runtime built **completely from scratch** in Python 3.11+ without external agent frameworks.

---

✨ Features & Requirement Mapping

| ID     | Feature                       | Implementation Details                                                                                                                                                 |
| :----- | :---------------------------- | :--------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| **R1** | **Resilient Agent Loop**      | Survives S1–S12 mock LLM scenarios (bad JSON, duplicate tool IDs, rate limits, dropped connections). Located in `agent/client.py` & `agent/loop.py`.                   |
| **R2** | **Durability & Exactly-Once** | SQLite WAL event-sourcing store (`agent/db.py`). Side-effects like `send_email` execute **exactly once**, even across abrupt `kill -9` process terminates.             |
| **R3** | **Context Budgeting**         | Hard ceiling of 8,000 tokens using `mockllm/tokenizer.py`. History automatically compacts (`agent/context.py`) when exceeding budget limits.                           |
| **R4** | **Structural Security**       | Strictly confines file operations to `workspace/`, restricts `http_get` to an allow-list, and enforces 5s wall-clock timeouts on `run_python` (`agent/tools/`).        |
| **R5** | **Loop & Cost Controls**      | Step ceiling (25 max steps) and fingerprint signature tracking to detect and terminate infinite tool loops (S4) in bounded time.                                       |
| **R6** | **Observability & Replay**    | Emits structured JSONL trace logs (`logs/`). Supports offline replay (`agent replay <run_id>`) without requiring a running server.                                     |
| **R7** | **Self-Checking Evals**       | Automated test suite (`evals/test_suite.py`) with 12 test cases, including 4 adversarial tests and **2 intentionally failing tests** documenting edge-case trade-offs. |
| **R8** | **Architecture Writeup**      | Architectural decisions and trade-offs documented in `DECISIONS.md` (≤1,000 words).                                                                                    |

🚀 Getting Started

Prerequisites

  - Python 3.11+
  - Standard library, sqlite3, and make

