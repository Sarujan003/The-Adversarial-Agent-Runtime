# evals/test_s9_duplicate_ids.py
import unittest
import sys
import time
from pathlib import Path

# Add project root to path to allow imports from agent package
sys.path.insert(0, str(Path(__file__).parent.parent))

from agent.loop import AgentLoop
from agent.client import ResilientLLMClient
from agent.db import StateStore

WORKSPACE_DIR = Path("workspace").resolve()
TEST_FILE = WORKSPACE_DIR / "s9_test.txt"

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

class TestS9DuplicateIDs(unittest.TestCase):
    def setUp(self):
        """Clean up test file before run."""
        if TEST_FILE.exists():
            TEST_FILE.unlink()

    def tearDown(self):
        """Clean up test file after run."""
        if TEST_FILE.exists():
            TEST_FILE.unlink()

    def test_s9_handles_duplicate_ids_across_turns(self):
        """R7 Eval: Tests S9 agent handles duplicate tool IDs across turns without crashing."""
        run_id = f"eval_s9_duplicate_ids_{int(time.time())}_{time.time_ns()}"
        task = "Write a file and then read it, in a scenario with duplicate tool IDs."

        agent = AgentLoop(run_id=run_id, task=task)
        agent.client = ScenarioLLMClient(agent.client.server_url, scenario_id="S9", run_id=run_id)
        agent.run()

        store = StateStore()
        events = store.get_events(run_id)

        tool_started_events = [e for e in events if e['event_type'] == 'TOOL_STARTED']
        tool_completed_events = [e for e in events if e['event_type'] == 'TOOL_COMPLETED']

        self.assertEqual(len(tool_started_events), 2, "Agent should have started two tools.")
        self.assertEqual(tool_started_events[0]['payload']['tool'], 'write_file')
        self.assertEqual(tool_started_events[1]['payload']['tool'], 'read_file')
        self.assertIn("First call with this ID.", tool_completed_events[1]['payload']['result'])

if __name__ == '__main__':
    unittest.main()