# Allow-listed HTTP GET client

import urllib.request
import urllib.error
from .base import is_domain_allowed

def tool_http_get(url: str) -> str:
    """R4 Safety: Allow-list enforced HTTP GET client."""
    if not is_domain_allowed(url):
        return f"Refusal: Access to domain in '{url}' is forbidden by policy."
    try:
        req = urllib.request.Request(url, headers={"User-Agent": "AgentRuntime/1.0"})
        with urllib.request.urlopen(req, timeout=5.0) as resp:
            content = resp.read().decode("utf-8")
            return content[:4000] # Truncate large payloads
    except Exception as e:
        return f"HTTP Error: {str(e)}"