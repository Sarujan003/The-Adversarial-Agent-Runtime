# evals/test_s3_nonexistent_tool.py
import unittest
import sys
import time
import json
from pathlib import Path

# Add project root to path to allow imports from agent package
sys.path.insert(0, str(Path(__file__).parent.parent))

from agent.loop import AgentLoop
from agent.client import ResilientLLMClient
from agent.db import StateStore

class ScenarioLLMClient(ResilientLLMClient):
    """A client that injects a scenario ID into requests."""
    def __init__(self, server_url: str, scenario_id: str):
        super().__init__(server_url)
        self.scenario_id = scenario_id

    def post_messages(self, messages: list, max_retries: int = 5, headers: dict = None) -> dict:
        # Override to inject the scenario header
        scenario_headers = {"X-Scenario-ID": self.scenario_id}
        return super().post_messages(messages, max_retries, headers=scenario_headers)

class TestS3NonExistentTool(unittest.TestCase):
    def test_s3_nonexistent_tool_handling(self):
        """R7 Eval: Tests S3 handling of a non-existent tool call."""
        run_id = f"eval_s3_no_tool_{int(time.time())}_{time.time_ns()}"
        task = "Execute the S3 test scenario for a non-existent tool."

        # 1. Setup agent with a client that requests the S3 scenario
        agent = AgentLoop(run_id=run_id, task=task)
        agent.client = ScenarioLLMClient(agent.client.server_url, scenario_id="S3")

        # 2. Run the agent
        agent.run()

        # 3. Assert that the agent correctly handled the error by checking the event log
        store = StateStore()
        events = store.get_events(run_id)

        tool_completed_event = next((e for e in events if e['event_type'] == 'tool_completed'), None)
        
        self.assertIsNotNone(tool_completed_event, "Agent should have logged a tool_completed event.")
        self.assertIn("Error: Tool 'non_existent_tool' does not exist.", tool_completed_event['payload']['result'])

if __name__ == '__main__':
    unittest.main()