# Transactional side-effect recorder

def tool_send_email(db_store, run_id: str, call_id: str, to: str, subject: str, body: str) -> str:
    """R2 Durability: Exactly-once email dispatch via SQLite transaction."""
    already_sent = db_store.execute_send_email_exactly_once(run_id, call_id, to, subject, body)
    if already_sent:
        return f"Email dispatch verified for {to} (Call ID: {call_id})."
    return f"Successfully sent email to {to}."