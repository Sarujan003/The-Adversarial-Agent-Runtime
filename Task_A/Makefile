# Makefile for Task A Agent Runtime

.PHONY: setup test eval run-server clean help

# Default target
help:
	@echo "Available Makefile targets:"
	@echo "  make setup       - Install dependencies using uv"
	@echo "  make test        - Run test suite"
	@echo "  make eval        - Run evals test suite"
	@echo "  make run-server  - Start local MockLLM server"
	@echo "  make clean       - Remove databases, logs, and cache files"

# Environment Setup
setup:
	uv venv .venv
	uv pip install -r requirements.txt

# Run Tests
test:
	python evals/test_suite.py

# Run Evals
eval:
	python evals/test_suite.py

# Start Mock Server
run-server:
	python mockllm/stub_server.py

# Cleanup
clean:
	rm -rf agent_state.db logs/*.jsonl workspace/* __pycache__ agent/__pycache__ agent/tools/__pycache__ evals/__pycache__ mockllm/__pycache__
