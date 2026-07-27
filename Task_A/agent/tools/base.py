# Workspace path resolution & security checks (R4)

from pathlib import Path
import urllib.parse

WORKSPACE_DIR = Path("workspace").resolve()
ALLOWED_DOMAINS = {"api.github.com", "httpbin.org", "localhost", "127.0.0.1"}

def safe_path(relative_path: str) -> Path:
    """R4 Safety: Enforces strict confinement within workspace/ directory."""
    WORKSPACE_DIR.mkdir(parents=True, exist_ok=True)
    target = (WORKSPACE_DIR / relative_path).resolve()
    if not target.is_relative_to(WORKSPACE_DIR):
        raise PermissionError(f"Security Boundary Violation: Path '{relative_path}' escapes workspace.")
    return target

def is_domain_allowed(url: str) -> bool:
    """R4 Safety: Checks host against allow-list."""
    parsed = urllib.parse.urlparse(url)
    return parsed.hostname in ALLOWED_DOMAINS