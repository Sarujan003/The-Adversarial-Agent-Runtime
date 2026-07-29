# stub_server.py
import json
import re
from http.server import HTTPServer, BaseHTTPRequestHandler

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