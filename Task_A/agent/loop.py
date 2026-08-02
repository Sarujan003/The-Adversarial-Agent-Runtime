import json
import html
import secrets
import concurrent.futures
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

    def close(self):
        """Closes any open resources, like the database connection."""
        self.store.close()

    def run(self):
        events = self.store.get_events(self.run_id)
        if not events:
            self.ctx.add_message("user", self.task)
            self._log_and_emit("task_started", {"task": self.task})
        else:
            self.seq = max(e["seq"] for e in events)

        step = 0
        should_stop = False
        while step < self.max_steps and not should_stop:
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
                response, salvage_used = self.client.post_messages(self.ctx.messages)
                print("Received response from MockLLM:", response)
            except TimeoutError as e: # Client raises TimeoutError after exhausting retries
                self._log_and_emit("error", {"message": str(e)})
                break
            except Exception as e: # Catch any other unexpected errors during client communication
                self._log_and_emit("error", {"message": f"Unexpected client communication error: {str(e)}"})
                break

            # S12: Partial / interrupted turn — surface observability event when salvage was used
            if salvage_used:
                self._log_and_emit("partial_turn_recovered", {"note": "Response was incomplete; _salvage_json recovered a partial turn."})

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

                # S11: Confidently wrong — model claims success when a prior tool returned an error.
                # Detect this by checking if the previous user message contained error tool results
                # while the model's text response asserts success.
                SUCCESS_PHRASES = ("successfully", "completed", "done", "retrieved", "finished", "achieved")
                ERROR_PREFIXES = ("Error:", "Error executing", "FileNotFoundError", "does not exist")
                prev_messages = self.ctx.messages
                last_tool_results = []
                for m in reversed(prev_messages):
                    if m.get("role") == "user" and isinstance(m.get("content"), list):
                        last_tool_results = [
                            c for c in m["content"]
                            if isinstance(c, dict) and c.get("type") == "tool_result"
                        ]
                        break
                prior_had_errors = any(
                    any(pfx in str(c.get("content", "")) for pfx in ERROR_PREFIXES)
                    for c in last_tool_results
                )
                model_claims_success = any(p in text_response.lower() for p in SUCCESS_PHRASES)
                if prior_had_errors and model_claims_success:
                    self._log_and_emit("model_assertion_mismatch", {
                        "model_text": text_response,
                        "note": "Model claimed success after tool returned an error."
                    })
                    # Inject a corrective message so the model knows the real state
                    error_details = "; ".join(
                        str(c.get("content", ""))[:120]
                        for c in last_tool_results
                        if any(pfx in str(c.get("content", "")) for pfx in ERROR_PREFIXES)
                    )
                    self.ctx.add_message(
                        "user",
                        f"Correction: One or more tools actually returned an error. "
                        f"Please acknowledge the failure and try a different approach. Error details: {error_details}"
                    )
                    continue

                # Otherwise, assume it's a multi-turn text conversation (like S8) and prompt to continue.
                self.ctx.add_message("user", "Please continue.")
                continue # Go to next loop iteration

            # --- Tool call processing ---
            # R1/S10: Handle parallel tool calls with failures and hangs
            tool_results_for_ctx = []
            calls_to_dispatch = []

            # Pre-dispatch checks (must be done sequentially)
            for call in tool_calls:
                call_id = call.get("id", "call_unknown")
                tool_name = call.get("name")
                args = call.get("input", {})

                # S4: Infinite Loop Detection
                sig = f"{tool_name}:{json.dumps(args, sort_keys=True)}"
                if self.call_history.count(sig) >= 3:
                    self._log_and_emit("terminated", {"reason": f"Infinite loop detected on tool '{tool_name}'"})
                    should_stop = True
                    break
                self.call_history.append(sig)

                # R4 Guardrail: Block privileged tools if they immediately follow a data-ingesting tool call.
                PRIVILEGED_TOOLS = {"send_email"}
                last_user_msg = self.ctx.messages[-2] if len(self.ctx.messages) > 1 else None
                is_prev_msg_tool_result = (
                    last_user_msg and last_user_msg.get('role') == 'user' and
                    isinstance(last_user_msg.get('content'), list) and
                    any(c.get('type') == 'tool_result' for c in last_user_msg['content'])
                )
                if tool_name in PRIVILEGED_TOOLS and is_prev_msg_tool_result:
                    rejection_reason = f"Security policy violation: Privileged tool '{tool_name}' was blocked because it was called immediately after a tool returned data. This is a defense against prompt injection."
                    self._log_and_emit("tool_rejected", {"call_id": call_id, "tool": tool_name, "reason": rejection_reason})
                    result = f"Error: {rejection_reason}"
                    tool_results_for_ctx.append({
                        "type": "tool_result",
                        "tool_use_id": call_id,
                        "content": result # This system-generated error does not need sanitization
                    })
                    continue # Skip dispatching this call
                
                self._log_and_emit("tool_started", {"call_id": call_id, "tool": tool_name})
                calls_to_dispatch.append(call)

            # If the loop-detection logic decided to stop, break out of the main while loop now.
            if should_stop:
                break

            # Concurrent dispatch of valid calls
            if calls_to_dispatch:
                with concurrent.futures.ThreadPoolExecutor() as executor:
                    future_to_call = {
                        executor.submit(self._dispatch_tool, call.get("id"), call.get("name"), call.get("input", {})): call
                        for call in calls_to_dispatch
                    }

                    # Wait for futures with a timeout (slightly longer than python_tool's internal timeout)
                    done, not_done = concurrent.futures.wait(future_to_call.keys(), timeout=7.0)

                    # Process completed futures (success or failure)
                    for future in done:
                        call = future_to_call[future]
                        try:
                            result = future.result()
                        except Exception as e:
                            result = f"Error executing tool '{call.get('name')}': {str(e)}"
                        
                        self._log_and_emit("tool_completed", {"call_id": call.get("id"), "result": result})
                        
                        # Sanitize and prepare for context
                        escaped_result = html.escape(str(result))
                        nonce = secrets.token_hex(4)
                        tag_name = f"untrusted_content_{nonce}"
                        sanitized_result = f"<{tag_name}>\n{escaped_result}\n</{tag_name}>"
                        tool_results_for_ctx.append({"type": "tool_result", "tool_use_id": call.get("id"), "content": sanitized_result})

                    # Process timed-out (hanging) futures
                    for future in not_done:
                        call = future_to_call[future]
                        result = f"Error: Tool '{call.get('name')}' timed out."
                        self._log_and_emit("tool_completed", {"call_id": call.get("id"), "result": result})
                        escaped_result = html.escape(str(result))
                        nonce = secrets.token_hex(4)
                        tag_name = f"untrusted_content_{nonce}"
                        sanitized_result = f"<{tag_name}>\n{escaped_result}\n</{tag_name}>"
                        tool_results_for_ctx.append({"type": "tool_result", "tool_use_id": call.get("id"), "content": sanitized_result})

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