# Core agent loop & step/loop controls (R1, R5)

import json
from typing import Dict, Any
from .db import StateStore
from .client import ResilientLLMClient
from .context import ContextManager
from .observability import JSONLTracer
from .tools import TOOL_REGISTRY

class AgentLoop:
    def __init__(self, run_id: str, task: str, server_url: str = "http://localhost:8000"):
        self.run_id = run_id
        self.task = task
        self.client = ResilientLLMClient(server_url)
        self.store = StateStore()
        self.tracer = JSONLTracer(run_id)
        self.ctx = ContextManager()
        self.seq = 0
        self.max_steps = 25
        self.call_history = []

    def _log_and_emit(self, event_type: str, payload: Dict[str, Any]):
        self.seq += 1
        self.store.append_event(self.run_id, self.seq, event_type, payload)
        self.tracer.emit(self.run_id, self.seq, event_type, payload)

    def run(self):
        events = self.store.get_events(self.run_id)
        if not events:
            self.ctx.add_message("user", self.task)
            self._log_and_emit("task_started", {"task": self.task})
        else:
            self.seq = max(e["seq"] for e in events)

        step = 0
        while step < self.max_steps:
            step += 1
            self.ctx.compact_if_needed()

            try:
                response = self.client.post_messages(self.ctx.messages)
            except Exception as e:
                self._log_and_emit("error", {"message": str(e)})
                break

            content = response.get("content", [])
            tool_calls = [c for c in content if isinstance(c, dict) and c.get("type") == "tool_use"]

            if not tool_calls:
                self._log_and_emit("completed", {"response": response})
                break

            for call in tool_calls:
                call_id = call.get("id", "call_unknown")
                tool_name = call.get("name")
                args = call.get("input", {})

                # S4: Infinite Loop Detection
                sig = f"{tool_name}:{json.dumps(args, sort_keys=True)}"
                if self.call_history.count(sig) >= 3:
                    self._log_and_emit("terminated", {"reason": f"Infinite loop detected on tool '{tool_name}'"})
                    return
                self.call_history.append(sig)

                self._log_and_emit("tool_started", {"call_id": call_id, "tool": tool_name})
                
                # Execute Tool
                result = self._dispatch_tool(call_id, tool_name, args)
                self._log_and_emit("tool_completed", {"call_id": call_id, "result": result})

                # R4 Injection Protection: Sanitize raw tool outputs to prevent prompt override hijacking
                sanitized_result = str(result).replace("SYSTEM:", "[INJECTION_NEUTRALIZED:]").replace("HUMAN:", "[TEXT:]")

                # Update context
                self.ctx.add_message("assistant", content)
                self.ctx.add_message("user", [{
                    "type": "tool_result",
                    "tool_use_id": call_id,
                    "content": sanitized_result
                }])


    def _dispatch_tool(self, call_id: str, tool_name: str, args: Dict[str, Any]) -> str:
        if tool_name not in TOOL_REGISTRY:
            return f"Error: Tool '{tool_name}' does not exist."
        try:
            fn = TOOL_REGISTRY[tool_name]
            if tool_name == "send_email":
                return fn(self.store, self.run_id, call_id, args.get("to",""), args.get("subject",""), args.get("body",""))
            return fn(**args)
        except Exception as e:
            return f"Error executing tool '{tool_name}': {str(e)}"