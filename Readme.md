# Adversarial Agent Runtime (Task A)

A durable, safe, and observable agent runtime built from scratch in Python without framework abstractions. Built to withstand hostile LLM behaviors (S1-S12) including malformed tool calls, rate limits, prompt injections, and infinite loops.

---

## 1. Project Directory Structure

```text
QNetwork_Task/
├── .gitignore
├── Readme.md
├── agent.md
├── candidate-brief.md
├── graph.md
├── testReport.md
└── Task_A/
    ├── DECISIONS.md
    ├── Makefile
    ├── TIMELOG.md
    ├── agent_state.db
    ├── commands.md
    ├── evals/
    │   ├── test_s1_happy_path.py
    │   ├── test_s2_malformed_json.py
    │   ├── test_s3_nonexistent_tool.py
    │   ├── test_s4_infinite_loop.py
    │   ├── test_s5_connection_reset.py
    │   ├── test_s6_rate_limit.py
    │   ├── test_s7_prompt_injection.py
    │   ├── test_s8_context_budget.py
    │   ├── test_s9_duplicate_ids.py
    │
    ├── mockllm/
    │   ├── scenarios/
    │   │   ├── s1.json
    │   │   ├── s2.json
    │   │   ├── s3.json
    │   │   ├── s4.json
    │   │   ├── s5.json
    │   │   ├── s6.json
    │   │   ├── s7.json
    │   │   ├── s8.json
    │   │   └── s9.json
    │   ├── stub_server.py     # Local Messages-API mock server (http://localhost:8000)
    │   └── tokenizer.py       # Deterministic token counter
    ├── requirements.txt
    ├── workspace/
    └── agent/
        ├── __init__.py
        ├── cli.py             # CLI entrypoint (run, resume, replay)
        ├── client.py          # Resilient HTTP client (S2, S5, S6 error handling)
        ├── context.py         # Token counting & context compaction with fact pinning
        ├── db.py              # SQLite event sourcing & transactional email store
        ├── loop.py            # Execution loop, loop detection & XML nonce injection protection
        ├── observability.py   # JSONL structured tracing & offline replay engine
        └── tools/
            ├── __init__.py
            ├── base.py        # Workspace path security & HTTP domain allow-list
            ├── email_tool.py   # Exactly-once email dispatcher
            ├── file_tools.py   # Sandboxed read_file & write_file
            ├── http_tool.py    # Allow-listed http_get client
            └── python_tool.py  # Subprocess run_python executor (5s timeout)
```

---

## 2. Environment Setup (using `uv`)

This project uses [`uv`](https://github.com/astral-sh/uv) as the fast Python package installer and virtual environment manager.

### Step 1: Create Virtual Environment
```bash
# Navigate to Task_A directory
cd Task_A

# Create virtual environment using uv
uv venv .venv
```

### Step 2: Activate Virtual Environment

- Windows (PowerShell):
  ```powershell
  .venv\Scripts\Activate.ps1
  ```
- Linux / macOS:
  ```bash
  source .venv/bin/activate
  ```

### Step 3: Install Dependencies
```bash
uv pip install -r requirements.txt
```

---

## 3. Running the Agent Runtime

### Step 1: Start Local Mock Server
Before running agent commands, start the local `mockllm` server in a separate terminal:

```bash
# In terminal 1 (inside Task_A directory):
python mockllm/stub_server.py
```

Server runs on `http://localhost:8000`.

---

### Step 2: Execute Agent Tasks (CLI)

Open a second terminal window with the virtual environment activated and inside the `Task_A` directory:

#### A. File Write Tool
```bash
python -m agent.cli run --task "Write 'hello world' to hello.txt" --run-id run_001
python -m agent.cli replay run_001
```

#### B. File Read Tool
```bash
python -m agent.cli run --task "Read hello.txt" --run-id run_002
python -m agent.cli replay run_002
```

#### C. Python Subprocess Execution Tool
```bash
python -m agent.cli run --task "Run python math calculation" --run-id run_py_01
python -m agent.cli replay run_py_01
```

#### D. Exactly-Once Email Dispatch Tool
```bash
python -m agent.cli run --task "Send email to 'admin@example.com'" --run-id run_email_01
python -m agent.cli replay run_email_01
```

#### E. Allow-Listed HTTP GET Tool
```bash
python -m agent.cli run --task "Fetch url http://localhost:8000" --run-id run_http_01
python -m agent.cli replay run_http_01
```

#### F. Resuming Process-Interrupted Runs
```bash
python -m agent.cli resume run_email_01
```

---

## 4. Running Automated Evals & Test Suite

To run the complete unit, functional, and security test suite:

```bash
# From Task_A directory:
The evaluation setup now includes:
- Scenario-specific tests in `Task_A/evals/test_s1_happy_path.py` through `test_s9_duplicate_ids.py`