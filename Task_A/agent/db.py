# SQLite event sourcing & transactional lock engine (R2)

import sqlite3
import json
from typing import Dict, Any, List

class StateStore:
    def __init__(self, db_path: str = "agent_state.db"):
        self.db_path = db_path
        self.conn = sqlite3.connect(self.db_path, timeout=30.0)
        self.conn.execute("PRAGMA journal_mode=WAL;")
        self.conn.execute("PRAGMA synchronous=NORMAL;")
        self._init_db()

    def close(self):
        if self.conn:
            self.conn.close()

    def _init_db(self):
        self.conn.execute("""
                CREATE TABLE IF NOT EXISTS event_log (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    run_id TEXT NOT NULL,
                    seq INTEGER NOT NULL,
                    event_type TEXT NOT NULL,
                    payload TEXT NOT NULL,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    UNIQUE(run_id, seq)
                );
            """)
        self.conn.execute("""
                CREATE TABLE IF NOT EXISTS emails (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    run_id TEXT NOT NULL,
                    call_id TEXT UNIQUE NOT NULL,
                    to_address TEXT NOT NULL,
                    subject TEXT NOT NULL,
                    body TEXT NOT NULL,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                );
            """)
        self.conn.commit()

    def append_event(self, run_id: str, seq: int, event_type: str, payload: Dict[str, Any]):
        self.conn.execute(
            "INSERT INTO event_log (run_id, seq, event_type, payload) VALUES (?, ?, ?, ?)",
            (run_id, seq, event_type, json.dumps(payload))
        )
        self.conn.commit()

    def get_events(self, run_id: str) -> List[Dict[str, Any]]:
        cursor = self.conn.cursor()
        cursor.execute("SELECT seq, event_type, payload FROM event_log WHERE run_id = ? ORDER BY seq ASC", (run_id,))
        return [{"seq": row[0], "event_type": row[1], "payload": json.loads(row[2])} for row in cursor.fetchall()]

    def execute_send_email_exactly_once(self, run_id: str, call_id: str, to_addr: str, subject: str, body: str) -> bool:
        """ Guarantees exactly-once side-effects under process kills (kill -9) """
        cursor = self.conn.cursor()
        cursor.execute("SELECT id FROM emails WHERE call_id = ?", (call_id,))
        if cursor.fetchone() is not None:
            return True  # Already executed in prior run attempt

        try:
            self.conn.execute(
                "INSERT INTO emails (run_id, call_id, to_address, subject, body) VALUES (?, ?, ?, ?, ?)",
                (run_id, call_id, to_addr, subject, body)
            )
            self.conn.commit()
            return False  # Newly inserted
        except sqlite3.IntegrityError:
            return True