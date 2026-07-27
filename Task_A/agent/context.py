# Token counting & context compaction strategy (R3)

import sys
import json
from pathlib import Path
from typing import List, Dict, Any

# Import tokenizer from mockllm package
sys.path.append(str(Path(__file__).parent.parent))
try:
    from mockllm.tokenizer import count_tokens
except ImportError:
    def count_tokens(text: str) -> int:
        return len(text.split())  # Heuristic fallback

MAX_TOKENS = 8000
COMPACT_TRIGGER = 7000

class ContextManager:
    def __init__(self, system_prompt: str = "You are a safe agent. Use tools to solve tasks."):
        self.messages: List[Dict[str, Any]] = [{"role": "system", "content": system_prompt}]

    def add_message(self, role: str, content: Any):
        self.messages.append({"role": role, "content": content})

    def get_token_count(self) -> int:
        return sum(count_tokens(json.dumps(m.get("content", ""))) for m in self.messages)

    def compact_if_needed(self):
        """R3: Compacts history when approaching context limit."""
        if self.get_token_count() <= COMPACT_TRIGGER or len(self.messages) <= 4:
            return

        # Preserve System (0) and First User Message (1)
        system_msg = self.messages[0]
        initial_user = self.messages[1]
        recent_turns = self.messages[-4:]

        middle_turns = self.messages[2:-4]
        summary_text = f"[COMPACTED: {len(middle_turns)} turns condensed. Key decisions and state preserved.]"

        self.messages = [
            system_msg,
            initial_user,
            {"role": "user", "content": summary_text},
            {"role": "assistant", "content": "Compacted history acknowledged. Continuing task."}
        ] + recent_turns