# evals/test_s6_rate_limit.py
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
    """A client that injects scenario and run IDs into requests."""
    def __init__(self, server_url: str, scenario_id: str, run_id: str):
        super().__init__(server_url)
        self.scenario_id = scenario_id
        self.run_id = run_id

    def post_messages(self, messages: list, max_retries: int = 5, headers: dict = None) -> dict:
        scenario_headers = {
            "X-Scenario-ID": self.scenario_id,
            "X-Run-ID": self.run_id
        }
        return super().post_messages(messages, max_retries, headers=scenario_headers)

class TestS6RateLimit(unittest.TestCase):
    def test_s6_rate_limit_recovery(self):
        """R7 Eval: Tests S6 rate limit (429/529) recovery."""
        run_id = f"eval_s6_rate_limit_{int(time.time())}_{time.time_ns()}"
        task = "Execute the S6 test scenario."

        # 1. Clean up previous run artifacts
        test_file = WORKSPACE_DIR / "s6_test.txt"
        if test_file.exists():
            test_file.unlink()

        # 2. Setup agent with a client that requests the S6 scenario
        agent = AgentLoop(run_id=run_id, task=task)
        agent.client = ScenarioLLMClient(agent.client.server_url, scenario_id="S6", run_id=run_id)

        # 3. Run the agent
        agent.run()

        # 4. Assert that the file was created, proving recovery and retry
        self.assertTrue(test_file.exists(), "Agent should have created s6_test.txt after rate limit retries.")
        content = test_file.read_text()
        self.assertEqual(content, "This is a test for the S6 rate limit scenario.")

if __name__ == '__main__':
    unittest.main()