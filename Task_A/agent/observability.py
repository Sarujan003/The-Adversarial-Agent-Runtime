# JSONL trace logging & offline replay runner (R6)

import json
from pathlib import Path
from typing import Dict, Any
from .db import StateStore

LOGS_DIR = Path("logs")

class JSONLTracer:
    def __init__(self, run_id: str):
        LOGS_DIR.mkdir(parents=True, exist_ok=True)
        self.trace_path = LOGS_DIR / f"trace_{run_id}.jsonl"

    def emit(self, run_id: str, seq: int, event_type: str, payload: Dict[str, Any]):
        record = {"run_id": run_id, "seq": seq, "event_type": event_type, "payload": payload}
        with open(self.trace_path, "a", encoding="utf-8") as f:
            f.write(json.dumps(record) + "\n")

def replay_run(run_id: str, db_path: str = "agent_state.db"):
    """R6: Offline replay runner that operates without the LLM server."""
    store = StateStore(db_path)
    events = store.get_events(run_id)
    print(f"\n--- Offline Replay for Run ID: {run_id} ({len(events)} events) ---")
    for evt in events:
        print(f"[{evt['seq']:03d}] {evt['event_type'].upper()}: {json.dumps(evt['payload'])}")