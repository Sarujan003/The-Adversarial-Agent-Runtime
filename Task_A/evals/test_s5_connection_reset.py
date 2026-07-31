# evals/test_s5_connection_reset.py
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

class TestS5ConnectionReset(unittest.TestCase):
    def test_s5_connection_reset_recovery(self):
        """R7 Eval: Tests S5 connection reset recovery."""
        run_id = f"eval_s5_reset_{int(time.time())}_{time.time_ns()}"
        task = "Execute the S5 test scenario."

        # 1. Clean up previous run artifacts
        test_file = WORKSPACE_DIR / "s5_test.txt"
        if test_file.exists():
            test_file.unlink()

        # 2. Setup agent with a client that requests the S5 scenario
        agent = AgentLoop(run_id=run_id, task=task)
        agent.client = ScenarioLLMClient(agent.client.server_url, scenario_id="S5", run_id=run_id)

        # 3. Run the agent
        agent.run()

        # 4. Assert that the file was created, proving recovery and retry
        self.assertTrue(test_file.exists(), "Agent should have created s5_test.txt after connection reset.")
        content = test_file.read_text()
        self.assertEqual(content, "This is a test for the S5 connection reset scenario.")

if __name__ == '__main__':
    unittest.main()