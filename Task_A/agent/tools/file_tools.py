# Sandboxed file read/write (workspace/)

from .base import safe_path

def tool_read_file(path: str) -> str:
    try:
        p = safe_path(path)
        if not p.exists():
            return f"Error: File '{path}' does not exist."
        return p.read_text(encoding="utf-8")
    except Exception as e:
        return f"Error reading file: {str(e)}"

def tool_write_file(path: str, content: str) -> str:
    try:
        p = safe_path(path)
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_text(content, encoding="utf-8")
        return f"Successfully wrote {len(content)} bytes to '{path}'."
    except Exception as e:
        return f"Error writing file: {str(e)}"