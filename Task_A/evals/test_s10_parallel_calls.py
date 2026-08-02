# evals/test_s10_parallel_calls.py
import unittest
import sys
import time
from pathlib import Path

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from agent.loop import AgentLoop
from agent.client import ResilientLLMClient
from agent.db import StateStore

WORKSPACE_DIR = Path("workspace").resolve()
TEST_FILE = WORKSPACE_DIR / "s10_test.txt"

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

class TestS10ParallelCalls(unittest.TestCase):
    def setUp(self):
        if TEST_FILE.exists():
            TEST_FILE.unlink()

    def tearDown(self):
        if TEST_FILE.exists():
            TEST_FILE.unlink()

    def test_s10_parallel_hang_and_fail(self):
        """R7 Eval: Tests S10 parallel tool calls with one hang and one fail."""
        run_id = f"eval_s10_parallel_{int(time.time())}_{time.time_ns()}"
        task = "Execute S10 scenario."

        agent = AgentLoop(run_id=run_id, task=task)
        agent.client = ScenarioLLMClient(agent.client.server_url, scenario_id="S10", run_id=run_id)
        
        start_time = time.time()
        agent.run()
        end_time = time.time()
        agent.close()

        # Assert agent didn't hang indefinitely
        self.assertLess(end_time - start_time, 10, "Agent should not hang for more than 10 seconds.")

        # Assert the successful call worked
        self.assertTrue(TEST_FILE.exists(), "Successful parallel call should have created the file.")
        self.assertEqual(TEST_FILE.read_text(), "S10 success")

        # Assert all three tool calls were processed and logged
        store = StateStore()
        events = store.get_events(run_id)
        store.close()
        
        started_events = [e for e in events if e['event_type'] == 'tool_started']
        completed_events = [e for e in events if e['event_type'] == 'tool_completed']

        self.assertEqual(len(started_events), 3, "Agent should have started all 3 parallel tools.")
        self.assertEqual(len(completed_events), 3, "Agent should have logged completion for all 3 parallel tools.")

        results = {e['payload']['call_id']: e['payload']['result'] for e in completed_events}
        self.assertIn("Error: File 'non_existent_file.txt' does not exist.", results.get("call_s10_fail", ""))
        self.assertIn("timed out", results.get("call_s10_hang", ""))
        self.assertIn("Successfully wrote", results.get("call_s10_ok", ""))

if __name__ == '__main__':
    unittest.main()