# agent/tools/python_tool.py
import sys
import subprocess
from pathlib import Path

WORKSPACE_DIR = Path("workspace").resolve()

def tool_run_python(code: str) -> str:
    """R4 Safety: Subprocess execution with wall-clock timeout and restricted cwd."""
    WORKSPACE_DIR.mkdir(parents=True, exist_ok=True)
    try:
        res = subprocess.run(
            [sys.executable, "-c", code],  # Uses active .venv python binary
            cwd=str(WORKSPACE_DIR),
            capture_output=True,
            text=True,
            timeout=5.0
        )
        output = (res.stdout + res.stderr).strip()
        return output if output else "Execution finished with no output."
    except subprocess.TimeoutExpired:
        return "Error: Python execution timed out (5s limit exceeded)."
    except Exception as e:
        return f"Error running Python process: {str(e)}"