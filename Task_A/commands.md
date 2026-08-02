# Task A CLI Command Reference & Evaluation Guide

This document provides a comprehensive command reference for testing, running, and evaluating all core tools and adversarial scenarios (S1–S12) implemented in **Task A**.

---

## 1. Environment & Server Startup

Before running any CLI or evaluation commands, activate your virtual environment and start the `mockllm` server:

```bash
# Navigate to Task_A directory
cd Task_A

# Activate virtual environment (PowerShell)
.venv\Scripts\Activate.ps1

# Terminal 1: Start MockLLM stub server (http://localhost:8000)
python mockllm/stub_server.py
```

---

## 2. Standalone Tool Execution Commands

Run task executions against the local agent runtime in Terminal 2:

### A. File Tools (`read_file`, `write_file`)
```bash
# Write file
python -m agent.cli run --task "Write 'Hello Task A' to notes.txt" --run-id run_write_01
python -m agent.cli replay run_write_01

# Read file
python -m agent.cli run --task "Read notes.txt" --run-id run_read_01
python -m agent.cli replay run_read_01
```

### B. Subprocess Execution (`run_python`)
```bash
python -m agent.cli run --task "Run python code 'for i in range(1, 4): print(i)'" --run-id run_py_01
python -m agent.cli replay run_py_01
```

### C. Exactly-Once Email Dispatch (`send_email`)
```bash
python -m agent.cli run --task "Send email to 'admin@example.com' subject 'Test' body 'Hello'" --run-id run_email_01
python -m agent.cli replay run_email_01

# Resume run after process kill (kill -9)
python -m agent.cli resume run_email_01
```

### D. Allow-Listed HTTP Client (`http_get`)
```bash
python -m agent.cli run --task "Fetch url http://localhost:8000" --run-id run_http_01
python -m agent.cli replay run_http_01
```

---

## 3. Adversarial Scenario Evaluation Suite (S1–S12)

Run scenario evaluation scripts under `evals/`:

```bash
# Run all 12 scenario test files
python evals/test_s1_happy_path.py
python evals/test_s2_malformed_json.py
python evals/test_s3_nonexistent_tool.py
python evals/test_s4_infinite_loop.py
python evals/test_s5_connection_reset.py
python evals/test_s6_rate_limit.py
python evals/test_s7_prompt_injection.py
python evals/test_s8_context_budget.py
python evals/test_s9_duplicate_ids.py
python evals/test_s10_parallel_calls.py
python evals/test_s11_confidently_wrong.py
python evals/test_s12_partial_turn.py
```

---

## 4. Offline Replay Commands

Inspect stored event traces for any run without contacting the LLM server:

```bash
python -m agent.cli replay <run_id>
```