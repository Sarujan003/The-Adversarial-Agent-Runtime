# evals/test_s11_confidently_wrong.py
import unittest
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from agent.loop import AgentLoop
from agent.client import ResilientLLMClient
from agent.db import StateStore


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


class TestS11ConfidentlyWrong(unittest.TestCase):
    def test_s11_mismatch_detected(self):
        """R7 Eval: S11 — agent detects that the model claimed success after a tool error."""
        run_id = f"eval_s11_{int(time.time())}_{time.time_ns()}"
        agent = AgentLoop(run_id=run_id, task="Read a file and report its contents.")
        agent.client = ScenarioLLMClient(agent.client.server_url, scenario_id="S11", run_id=run_id)
        agent.run()
        agent.close()

        store = StateStore()
        events = store.get_events(run_id)
        store.close()

        mismatch_events = [e for e in events if e["event_type"] == "model_assertion_mismatch"]
        self.assertTrue(
            len(mismatch_events) >= 1,
            f"Expected at least one model_assertion_mismatch event, got: {[e['event_type'] for e in events]}"
        )
        # Ensure mismatch payload contains the model text
        payload = mismatch_events[0]["payload"]
        self.assertIn("model_text", payload)
        self.assertIn("note", payload)

    def test_s11_agent_does_not_crash(self):
        """S11 — agent must survive the confidently-wrong turn without crashing."""
        run_id = f"eval_s11_nc_{int(time.time())}_{time.time_ns()}"
        agent = AgentLoop(run_id=run_id, task="Read a file.")
        agent.client = ScenarioLLMClient(agent.client.server_url, scenario_id="S11", run_id=run_id)
        try:
            agent.run()
            agent.close()
            crashed = False
        except Exception:
            crashed = True
        self.assertFalse(crashed, "Agent must not crash on S11 confidently-wrong scenario.")


if __name__ == "__main__":
    unittest.main()
