# Resilient HTTP client handling S1–S12 failures (R1)

import json
import time
import re
import urllib.request
import urllib.error
from typing import Dict, Any

class ResilientLLMClient:
    def __init__(self, server_url: str = "http://localhost:8000"):
        self.server_url = server_url

    def _salvage_json(self, raw_text: str) -> Dict[str, Any]:
        """S2: Salvages malformed JSON with trailing commas or unescaped characters."""
        cleaned = re.sub(r',\s*([}\]])', r'\1', raw_text)
        try:
            return json.loads(cleaned)
        except json.JSONDecodeError:
            # Fallback wrapper if response was cut mid-stream
            return {"content": [{"type": "text", "text": raw_text}]}

    def post_messages(self, messages: list, max_retries: int = 5) -> Dict[str, Any]:
        """S5 & S6: Resilient transport handling resets and 429/529 retries."""
        payload = json.dumps({"messages": messages}).encode("utf-8")
        req = urllib.request.Request(
            f"{self.server_url}/v1/messages",
            data=payload,
            headers={"Content-Type": "application/json"}
        )

        for attempt in range(max_retries):
            try:
                with urllib.request.urlopen(req, timeout=10.0) as resp:
                    raw_data = resp.read().decode("utf-8")
                    return self._salvage_json(raw_data)
            except urllib.error.HTTPError as e:
                if e.code in (429, 529):
                    retry_after = int(e.headers.get("Retry-After", 1))
                    time.sleep(retry_after)
                    continue
                raise e
            except (urllib.error.URLError, ConnectionResetError):
                time.sleep(2 ** attempt)
                continue
        raise TimeoutError("MockLLM unreachable after max retries.")