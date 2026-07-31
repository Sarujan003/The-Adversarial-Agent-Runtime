# stub_server.py
import json
import re
from pathlib import Path
import random
from http.server import HTTPServer, BaseHTTPRequestHandler

SCENARIOS_DIR = Path(__file__).parent / "scenarios"
S5_RESET_TRACKER = set()
S6_SEQUENCE_TRACKER = {}
MULTI_TURN_TRACKER = {}

class DynamicLLMHandler(BaseHTTPRequestHandler):
    def do_GET(self):
        self.send_response(200)
        self.send_header('Content-Type', 'text/html')
        self.end_headers()
        self.wfile.write(b"<html><body><h1>Mock HTTP Server Response OK</h1></body></html>")

    def do_POST(self):
        content_length = int(self.headers.get('Content-Length', 0))
        body = self.rfile.read(content_length)
        payload = json.loads(body.decode('utf-8'))
        messages = payload.get("messages", [])

        # Handle Scenarios First
        scenario_id = self.headers.get('X-Scenario-ID')
        if scenario_id:
            scenario_file = SCENARIOS_DIR / f"{scenario_id.lower()}.json"
            if scenario_file.exists():
                # S6: Rate limit simulation (random sequence of 429/529, then 200)
                if scenario_id.lower() == 's6':
                    run_id = self.headers.get('X-Run-ID')
                    if run_id:
                        if run_id not in S6_SEQUENCE_TRACKER:
                            num_errors = random.randint(2, 3)
                            S6_SEQUENCE_TRACKER[run_id] = random.choices([429, 529], k=num_errors)

                        if S6_SEQUENCE_TRACKER.get(run_id):
                            error_code = S6_SEQUENCE_TRACKER[run_id].pop(0)
                            self.send_response(error_code)
                            self.send_header('Content-Type', 'application/json')
                            if error_code == 429:
                                self.send_header('Retry-After', '1')
                            self.end_headers()
                            self.wfile.write(b'{"error": "Rate limit or overload"}')
                            return
                        
                        # If error sequence is done, serve the 200 OK response ONCE.
                        # On subsequent calls, the agent will have sent a tool_result, so we fall through.
                        last_msg = messages[-1] if messages else {}
                        if last_msg.get("role") == "user" and isinstance(last_msg.get("content"), str): # First turn
                            self.send_response(200); self.send_header('Content-Type', 'application/json'); self.end_headers()
                            self.wfile.write(scenario_file.read_bytes()); return
                # S5: Connection reset simulation
                elif scenario_id.lower() == 's5':
                    run_id = self.headers.get('X-Run-ID')
                    if run_id and run_id not in S5_RESET_TRACKER:
                        S5_RESET_TRACKER.add(run_id)
                        full_content = scenario_file.read_bytes()
                        # Send a partial response then close the connection
                        self.send_response(200)
                        self.send_header('Content-Type', 'application/json')
                        # Lie about content length to trigger IncompleteRead on client
                        self.send_header('Content-Length', str(len(full_content)))
                        self.end_headers()
                        self.wfile.write(full_content[:15]) # Write a small, incomplete chunk
                        # By not finishing the write, we simulate a connection reset.
                        return

                # S4, S7, S8, S9: Handle multi-turn scenarios.
                elif scenario_id.lower() in ['s4', 's7', 's8', 's9']:
                    try:
                        scenario_data = json.loads(scenario_file.read_text(encoding="utf-8"))
                        if isinstance(scenario_data, list):
                            run_id = self.headers.get('X-Run-ID')
                            if run_id not in MULTI_TURN_TRACKER:
                                MULTI_TURN_TRACKER[run_id] = 0
                            turn_index = MULTI_TURN_TRACKER[run_id]
                            
                            if scenario_id.lower() == 's4': # Infinite loop
                                response_index = min(turn_index, len(scenario_data) - 1)
                                response = scenario_data[response_index]
                                self.send_response(200); self.send_header('Content-Type', 'application/json'); self.end_headers()
                                self.wfile.write(json.dumps(response).encode('utf-8'))
                                if turn_index < len(scenario_data) - 1:
                                    MULTI_TURN_TRACKER[run_id] += 1
                                return

                            if scenario_id.lower() in ['s7', 's8', 's9']: # Sequential, then stop
                                if turn_index >= len(scenario_data):
                                    # If we run out of scripted turns, end the conversation gracefully.
                                    response = {"content": [{"type": "text", "text": "Scenario ended."}]}
                                else:
                                    response = scenario_data[turn_index]
                                self.send_response(200); self.send_header('Content-Type', 'application/json'); self.end_headers()
                                self.wfile.write(json.dumps(response).encode('utf-8'))
                                MULTI_TURN_TRACKER[run_id] += 1
                                return

                    except json.JSONDecodeError:
                        pass # Fall through if s4.json is not a valid list

                # Single-turn scenarios (S1, S2, S3)
                elif scenario_id.lower() in ['s1', 's2', 's3']:
                    last_msg = messages[-1] if messages else {}
                    is_first_turn = last_msg.get("role") == "user" and isinstance(last_msg.get("content"), str)
                    if is_first_turn:
                        self.send_response(200); self.send_header('Content-Type', 'application/json'); self.end_headers()
                        self.wfile.write(scenario_file.read_bytes()); return

        # Fallback to dynamic logic if no scenario was handled
        last_msg = messages[-1] if messages else {}
        last_content = str(last_msg.get("content", ""))

        self.send_response(200)
        self.send_header('Content-Type', 'application/json')
        self.end_headers()

        print("Received messages:", messages)

        # Step 1: If tool_result was returned, finish the run
        if isinstance(last_msg.get("content"), list) and any(
            isinstance(c, dict) and c.get("type") == "tool_result" 
            for c in last_msg.get("content", [])
        ):
            response = {
                "content": [{
                    "type": "text",
                    "text": "Task finished successfully!"
                }]
            }
            self.wfile.write(json.dumps(response).encode('utf-8'))
            return

        # Step 2: Extract Content from CLI prompt (inside quotes or after keywords)
        quote_match = re.search(r'["\'](.*?)["\']', last_content)
        if quote_match:
            file_content = quote_match.group(1)
        else:
            keyword_match = re.search(r'(?:with content|saying|containing|text)\s+(.*)', last_content, re.IGNORECASE)
            file_content = keyword_match.group(1) if keyword_match else "Default content"

        # Step 3: Check Tool Keywords
        if any(w in last_content.lower() for w in ["email", "send_email", "mail"]):
            email_to = quote_match.group(1) if quote_match else "admin@example.com"
            response = {
                "content": [{
                    "type": "tool_use",
                    "id": "call_email_01",
                    "name": "send_email",
                    "input": {
                        "to": email_to,
                        "subject": "Task Update",
                        "body": "Your task request has been processed successfully."
                    }
                }]
            }
        elif any(w in last_content.lower() for w in ["write", "create", "make", "save"]):
            file_match = re.search(r'[\w\-]+\.[a-zA-Z0-9]+', last_content)
            filename = file_match.group(0) if file_match else "default.txt"
            response = {
                "content": [{
                    "type": "tool_use",
                    "id": f"call_write_{filename}",
                    "name": "write_file",
                    "input": {"path": filename, "content": file_content}
                }]
            }
        elif "python" in last_content.lower() or "calc" in last_content.lower():
            python_code = file_content if quote_match else "print(2 + 2)"
            response = {
                "content": [{
                    "type": "tool_use",
                    "id": "call_py_01",
                    "name": "run_python",
                    "input": {"code": python_code}
                }]
            }
        elif any(w in last_content.lower() for w in ["http", "get", "fetch", "url"]):
            url_match = re.search(r'https?://[^\s"\']+', last_content)
            target_url = url_match.group(0) if url_match else "http://localhost:8000"
            response = {
                "content": [{
                    "type": "tool_use",
                    "id": "call_http_01",
                    "name": "http_get",
                    "input": {"url": target_url}
                }]
            }
        else:
            file_match = re.search(r'[\w\-]+\.[a-zA-Z0-9]+', last_content)
            filename = file_match.group(0) if file_match else "default.txt"
            response = {
                "content": [{
                    "type": "tool_use",
                    "id": f"call_read_{filename}",
                    "name": "read_file",
                    "input": {"path": filename}
                }]
            }

        self.wfile.write(json.dumps(response).encode('utf-8'))


if __name__ == '__main__':
    print("Smart Dynamic LLM running on http://localhost:8000 ...")
    server = HTTPServer(('localhost', 8000), DynamicLLMHandler)
    server.serve_forever()