# evals/test_s2_malformed_json.py
import unittest
import sys
import time
from pathlib import Path

# Add project root to path to allow imports from agent package
sys.path.insert(0, str(Path(__file__).parent.parent))

from agent.loop import AgentLoop
from agent.client import ResilientLLMClient

WORKSPACE_DIR = Path("workspace").resolve()

class ScenarioLLMClient(ResilientLLMClient):
    """A client that injects a scenario ID into requests."""
    def __init__(self, server_url: str, scenario_id: str):
        super().__init__(server_url)
        self.scenario_id = scenario_id

    def post_messages(self, messages: list, max_retries: int = 5, headers: dict = None) -> dict:
        # Override to inject the scenario header
        scenario_headers = {"X-Scenario-ID": self.scenario_id}
        return super().post_messages(messages, max_retries, headers=scenario_headers)

class TestS2MalformedJson(unittest.TestCase):
    def test_s2_malformed_json_recovery(self):
        """R7 Eval: Tests S2 malformed JSON recovery."""
        # Use a unique run_id for each test execution to ensure isolation from the DB.
        run_id = f"eval_s2_malformed_json_{int(time.time())}_{time.time_ns()}"
        task = "Execute the S2 test scenario."
        
        # 1. Clean up previous run artifacts if they exist
        test_file = WORKSPACE_DIR / "s2_test.txt"
        if test_file.exists():
            test_file.unlink()
        
        # 2. Setup agent with a client that requests the S2 scenario
        agent = AgentLoop(run_id=run_id, task=task)
        agent.client = ScenarioLLMClient(agent.client.server_url, scenario_id="S2")
        
        # 3. Run the agent
        agent.run()
        
        # 4. Assert that the file was created with the correct content
        self.assertTrue(test_file.exists(), "The agent should have created s2_test.txt after salvaging JSON.")
        content = test_file.read_text()
        self.assertEqual(content, "This is a test for the S2 malformed JSON scenario.")

if __name__ == '__main__':
    unittest.main()