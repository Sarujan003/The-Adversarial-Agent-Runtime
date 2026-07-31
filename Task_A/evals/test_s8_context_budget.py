# evals/test_s8_context_budget.py
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

class TestS8ContextBudget(unittest.TestCase):
    def test_s8_context_budget_exceeded(self):
        """R7 Eval: Tests S8 context budget is handled gracefully."""
        run_id = f"eval_s8_budget_{int(time.time())}_{time.time_ns()}"
        task = "Keep responding to me with long answers."

        # 1. Setup agent with a client that requests the S8 scenario
        agent = AgentLoop(run_id=run_id, task=task)
        agent.client = ScenarioLLMClient(agent.client.server_url, scenario_id="S8", run_id=run_id)

        # 2. Run the agent
        agent.run()


if __name__ == '__main__':
    unittest.main()