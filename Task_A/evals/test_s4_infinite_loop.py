# evals/test_s4_infinite_loop.py
import unittest
import sys
import time
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

class TestS4InfiniteLoop(unittest.TestCase):
    def test_s4_loop_detection(self):
        """R7 Eval: Tests S4 infinite loop detection and graceful termination."""
        run_id = f"eval_s4_infinite_loop_{int(time.time())}_{time.time_ns()}"
        task = "Execute the S4 test scenario to trigger a loop."

        # 1. Setup agent with a client that requests the S4 scenario
        agent = AgentLoop(run_id=run_id, task=task)
        agent.client = ScenarioLLMClient(agent.client.server_url, scenario_id="S4")

        # 2. Run the agent
        agent.run()

        # 3. Assert that the agent terminated due to loop detection
        store = StateStore()
        events = store.get_events(run_id)

        terminated_event = next((e for e in events if e['event_type'] == 'TERMINATED'), None)
        
        self.assertIsNotNone(terminated_event, "Agent should have logged a TERMINATED event.")
        self.assertIn("Infinite loop detected", terminated_event['payload']['reason'])

if __name__ == '__main__':
    unittest.main()