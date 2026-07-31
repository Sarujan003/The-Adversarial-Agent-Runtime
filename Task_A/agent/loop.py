import json
import html
import secrets
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
            try:
                self.ctx.compact_if_needed()
                print("Current context token count:", self.ctx.get_token_count())
            except ValueError as e:
                # R3: Gracefully terminate if context budget is irrecoverably blown.
                if "Context budget" in str(e):
                    self._log_and_emit("terminated", {"reason": f"Context budget exceeded: {str(e)}"})
                    break
                raise e # Re-raise other unexpected ValueErrors

            try:
                response = self.client.post_messages(self.ctx.messages)
                print("Received response from MockLLM:", response)
            except TimeoutError as e: # Client raises TimeoutError after exhausting retries
                self._log_and_emit("error", {"message": str(e)})
                break
            except Exception as e: # Catch any other unexpected errors during client communication
                self._log_and_emit("error", {"message": f"Unexpected client communication error: {str(e)}"})
                break

            content = response.get("content", [])
            tool_calls = [c for c in content if isinstance(c, dict) and c.get("type") == "tool_use"]

            # Add the assistant's response to the context first
            self.ctx.add_message("assistant", content)

            if not tool_calls:
                # This is a text-only response. Check for completion keywords.
                text_response = "".join(c.get("text", "") for c in content if c.get("type") == "text")
                if "Task finished" in text_response or "Scenario ended" in text_response:
                    self._log_and_emit("completed", {"response": response})
                    break
                # Otherwise, assume it's a multi-turn text conversation (like S8) and prompt to continue.
                self.ctx.add_message("user", "Please continue.")
                continue # Go to next loop iteration

            # --- Tool call processing ---
            tool_results_for_ctx = []
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

                # R4 Guardrail: Block privileged tools if they immediately follow a data-ingesting tool call.
                PRIVILEGED_TOOLS = {"send_email"}
                if tool_name in PRIVILEGED_TOOLS:
                    # Check if the last message sent to the LLM was a tool result.
                    # The message before the assistant's current turn (-2) is the one that prompted this tool call.
                    last_user_msg = self.ctx.messages[-2] if len(self.ctx.messages) > 1 else None
                    is_prev_msg_tool_result = (
                        last_user_msg and last_user_msg.get('role') == 'user' and
                        isinstance(last_user_msg.get('content'), list) and
                        any(c.get('type') == 'tool_result' for c in last_user_msg['content'])
                    )
                    if is_prev_msg_tool_result:
                        rejection_reason = f"Security policy violation: Privileged tool '{tool_name}' was blocked because it was called immediately after a tool returned data. This is a defense against prompt injection."
                        self._log_and_emit("tool_rejected", {"call_id": call_id, "tool": tool_name, "reason": rejection_reason})
                        result = f"Error: {rejection_reason}"
                        tool_results_for_ctx.append({
                            "type": "tool_result",
                            "tool_use_id": call_id,
                            "content": result # This system-generated error does not need sanitization
                        })
                        continue # Skip to the next tool call

                self._log_and_emit("tool_started", {"call_id": call_id, "tool": tool_name})
                
                # Execute Tool
                result = self._dispatch_tool(call_id, tool_name, args)
                self._log_and_emit("tool_completed", {"call_id": call_id, "result": result})

                # R4 Injection Protection (Defense-in-Depth):
                # 1. Escape HTML/XML entities (< -> &lt;, > -> &gt;)
                escaped_result = html.escape(str(result))
                
                # 2. Generate dynamic secure nonce using `secrets` module
                nonce = secrets.token_hex(4)
                tag_name = f"untrusted_content_{nonce}"
                
                # 3. Wrap in dynamic randomized XML boundary tags
                sanitized_result = f"<{tag_name}>\n{escaped_result}\n</{tag_name}>"

                # in real development, can use llama guard2 model to classify the known vulnerabilities.
                # after the classification, can block the remaining execution.

                # or can create vector database for the known vulnerabilities,
                # and then can use the vector database to classify the known vulnerabilities.

                tool_results_for_ctx.append({
                    "type": "tool_result",
                    "tool_use_id": call_id,
                    "content": sanitized_result
                })

            # Add all tool results for this turn to the context
            if tool_results_for_ctx:
                self.ctx.add_message("user", tool_results_for_ctx)

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