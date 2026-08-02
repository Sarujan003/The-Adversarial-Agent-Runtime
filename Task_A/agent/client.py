# Resilient HTTP client handling S1–S12 failures (R1)

import json
import time
import re
import urllib.request
import urllib.error
import http.client
from typing import Dict, Any

class ResilientLLMClient:
    def __init__(self, server_url: str = "http://localhost:8000"):
        self.server_url = server_url

    def _salvage_json(self, raw_text: str) -> Dict[str, Any]:
        """S2/S12: Salvages malformed/truncated JSON with trailing commas, unescaped chars, or cut-off streams."""
        cleaned = re.sub(r',\s*([}\]])', r'\1', raw_text.strip())

        print("Raw JSON:", raw_text)
        print("Cleaned JSON:", cleaned)

        # Try strict parse first
        try:
            parsed = json.loads(cleaned)
            if isinstance(parsed, dict) and "content" in parsed:
                print("Parsed JSON:", parsed)
                return parsed
        except json.JSONDecodeError:
            pass

        # Stack-based recovery: walk the string tracking nesting and string state
        for trim in range(len(cleaned), max(0, len(cleaned) - 30), -1):
            candidate = cleaned[:trim]
            
            # Walk through to track string state and nesting stack
            in_string = False
            stack = []  # tracks order of '{' and '['
            k = 0
            while k < len(candidate):
                ch = candidate[k]
                if ch == '\\' and in_string and k + 1 < len(candidate):
                    k += 2  # skip escaped char
                    continue
                if ch == '"':
                    in_string = not in_string
                elif not in_string:
                    if ch in ('{', '['):
                        stack.append(ch)
                    elif ch == '}' and stack and stack[-1] == '{':
                        stack.pop()
                    elif ch == ']' and stack and stack[-1] == '[':
                        stack.pop()
                k += 1

            # If inside an open string, close it
            suffix = '"' if in_string else ''
            
            # Remove any trailing comma after closing the string
            test = candidate + suffix
            test = re.sub(r',\s*$', '', test)
            
            # Close nesting in reverse order (innermost first)
            for opener in reversed(stack):
                test += '}' if opener == '{' else ']'

            try:
                parsed = json.loads(test)
                if isinstance(parsed, dict) and "content" in parsed:
                    print("Parsed JSON:", parsed)
                    return parsed
            except json.JSONDecodeError:
                continue

        return {"content": [{"type": "text", "text": "Error: Received malformed JSON response from MockLLM."}]}

    def post_messages(self, messages: list, max_retries: int = 5, headers: Dict[str, str] = None) -> tuple:
        """S5 & S6: Resilient transport handling resets and 429/529 retries.
        Returns (response_dict, salvage_used: bool) where salvage_used=True if
        _salvage_json had to repair a malformed or truncated response body (S2, S12).
        """
        payload = json.dumps({"messages": messages}).encode("utf-8")
        request_headers = {"Content-Type": "application/json"}
        if headers:
            request_headers.update(headers)

        req = urllib.request.Request(
            f"{self.server_url}/v1/messages", data=payload, headers=request_headers
        )

        for attempt in range(max_retries):
            try:
                with urllib.request.urlopen(req, timeout=10.0) as resp:
                    raw_data = resp.read().decode("utf-8")
                    # Try strict parse first; only call _salvage_json on failure
                    try:
                        return json.loads(raw_data), False
                    except json.JSONDecodeError:
                        return self._salvage_json(raw_data), True
            except urllib.error.HTTPError as e:
                if e.code in (429, 529):
                    retry_after = int(e.headers.get("Retry-After", 1))
                    print("Received HTTPError:", e.code, "Retrying after", retry_after, "seconds.")
                    time.sleep(retry_after)
                    continue
                raise e
            except http.client.IncompleteRead as e:
                # S12: Partial stream recovery - salvage partial response bytes
                if e.partial:
                    try:
                        raw_data = e.partial.decode("utf-8")
                        return self._salvage_json(raw_data), True
                    except Exception:
                        pass
                print(f"IncompleteRead occurred. Retrying attempt {attempt + 1}/{max_retries}...")
                time.sleep(2 ** attempt)
                continue
            except (urllib.error.URLError, ConnectionResetError) as e:
                print(f"Connection error/reset occurred ({type(e).__name__}). Retrying attempt {attempt + 1}/{max_retries}...")
                time.sleep(2 ** attempt)
                continue
        raise TimeoutError("MockLLM unreachable after max retries.")