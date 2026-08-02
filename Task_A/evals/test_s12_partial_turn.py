# evals/test_s12_partial_turn.py
import unittest
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from agent.loop import AgentLoop
from agent.client import ResilientLLMClient
from agent.db import StateStore

WORKSPACE_DIR = (Path(__file__).parent.parent / "workspace").resolve()
TEST_FILE = WORKSPACE_DIR / "s12_test.txt"


class ScenarioLLMClient(ResilientLLMClient):
    """Injects scenario and run IDs into every request."""
    def __init__(self, server_url: str, scenario_id: str, run_id: str):
        super().__init__(server_url)
        self.scenario_id = scenario_id
        self.run_id = run_id

    def post_messages(self, messages: list, max_retries: int = 5, headers: dict = None) -> tuple:
        scenario_headers = {
            "X-Scenario-ID": self.scenario_id,
            "X-Run-ID": self.run_id,
        }
        return super().post_messages(messages, max_retries, headers=scenario_headers)


class TestS12PartialTurn(unittest.TestCase):
    def setUp(self):
        if TEST_FILE.exists():
            TEST_FILE.unlink()

    def tearDown(self):
        if TEST_FILE.exists():
            TEST_FILE.unlink()

    def test_s12_partial_turn_recovered(self):
        """R7 Eval: S12 — agent recovers from a partial/interrupted turn and logs the event."""
        run_id = f"eval_s12_{int(time.time())}_{time.time_ns()}"
        agent = AgentLoop(run_id=run_id, task="Write a test file using three parallel tool calls.")
        agent.client = ScenarioLLMClient(agent.client.server_url, scenario_id="S12", run_id=run_id)
        agent.run()
        agent.close()

        store = StateStore()
        events = store.get_events(run_id)
        store.close()

        # The partial_turn_recovered event must have been emitted
        recovery_events = [e for e in events if e["event_type"] == "partial_turn_recovered"]
        self.assertTrue(
            len(recovery_events) >= 1,
            f"Expected at least one partial_turn_recovered event, got: {[e['event_type'] for e in events]}"
        )

    def test_s12_agent_does_not_crash(self):
        """S12 — agent must survive a partial/interrupted response without crashing."""
        run_id = f"eval_s12_nc_{int(time.time())}_{time.time_ns()}"
        agent = AgentLoop(run_id=run_id, task="Write a test file.")
        agent.client = ScenarioLLMClient(agent.client.server_url, scenario_id="S12", run_id=run_id)
        try:
            agent.run()
            agent.close()
            crashed = False
        except Exception:
            crashed = True
        self.assertFalse(crashed, "Agent must not crash on S12 partial turn scenario.")

    def test_s12_successful_tool_executes(self):
        """S12 — the tool call recovered from the partial turn must still execute."""
        run_id = f"eval_s12_tool_{int(time.time())}_{time.time_ns()}"
        agent = AgentLoop(run_id=run_id, task="Write a test file named s12_test.txt with content 'S12 partial turn recovered'.")
        agent.client = ScenarioLLMClient(agent.client.server_url, scenario_id="S12", run_id=run_id)
        agent.run()
        agent.close()

        self.assertTrue(
            TEST_FILE.exists(),
            "write_file recovered from partial turn should have created s12_test.txt"
        )


if __name__ == "__main__":
    unittest.main()
