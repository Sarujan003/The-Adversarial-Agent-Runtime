# Dynamic tool execution router

from typing import Dict, Callable, Any
from .file_tools import tool_read_file, tool_write_file
from .python_tool import tool_run_python
from .http_tool import tool_http_get
from .email_tool import tool_send_email

TOOL_REGISTRY: Dict[str, Callable] = {
    "read_file": tool_read_file,
    "write_file": tool_write_file,
    "run_python": tool_run_python,
    "http_get": tool_http_get,
    "send_email": tool_send_email
}