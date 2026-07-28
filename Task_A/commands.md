# Task A CLI Command Reference & Test Guide

This document lists all available CLI commands to test and verify the tools and requirements implemented in Task A.

---

## 1. File Tools (`read_file`, `write_file`)

### Read File
```bash
# Execute task to read a workspace file
python -m agent.cli run --task "Read dummy.txt" --run-id run_read_01

# Replay offline trace
python -m agent.cli replay run_read_01
```

### Write File
```bash
# Execute task to write a workspace file
python -m agent.cli run --task "Write notes.txt with content 'Hello from CLI'" --run-id run_write_01

# Replay offline trace
python -m agent.cli replay run_write_01
```

---

## 2. Python Code Execution (`run_python`)

```bash
# Execute python code snippet
python -m agent.cli run --task "Run python math calculation" --run-id run_py_01

# Replay offline trace
python -m agent.cli replay run_py_01

# Example 2: Loop execution
python -m agent.cli run --task "Run python code 'for i in range(1, 4): print(i)'" --run-id run_py_07
python -m agent.cli replay run_py_07
```

---

## 3. Email Side-Effect & Exactly-Once Durability (`send_email`)

```bash
# Send simulated email (appends row to SQLite emails table)
python -m agent.cli run --task "Send email to 'admin@example.com'" --run-id run_email_01

# Replay offline trace
python -m agent.cli replay run_email_01

# Resume task run after process interrupt/kill
python -m agent.cli resume run_email_01
```

---

## 4. HTTP Allow-List Client (`http_get`)

```bash
# Fetch from allowed local endpoint
python -m agent.cli run --task "Fetch url http://localhost:8000" --run-id run_http_01

# Replay offline trace
python -m agent.cli replay run_http_01
```

---

## 5. Automated Evaluation & Security Suite

```bash
# Run Unit & Adversarial Security Test Suite
python Task_A/evals/test_suite.py
```