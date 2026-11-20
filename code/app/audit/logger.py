"""
Append-only audit trail. Every agent action — auto-executed, human-queued,
or failed — writes exactly one line here. Append-only + on disk means the
record can't be quietly rewritten, which is the point of an audit log.

Each entry answers: when, what happened, what the agent reasoned, what the
guardrail decided, and how it ended.
"""
import json
import uuid
from datetime import datetime, timezone

from app.config import AUDIT_LOG_PATH


def log_event(
    event: str,
    reasoning: str,
    guardrail_result: str,
    outcome: str,
    provider: str = "",
    extra: dict | None = None,
) -> dict:
    entry = {
        "id": str(uuid.uuid4()),
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "event": event,                 # e.g. "checkout_attempt", "upsell_offered"
        "provider": provider,           # which brain reasoned ("anthropic"/"offline")
        "reasoning": reasoning,         # the agent's short rationale
        "guardrail_result": guardrail_result,
        "outcome": outcome,             # "auto_executed" | "queued_for_human" | "failed" | ...
        "extra": extra or {},
    }
    with AUDIT_LOG_PATH.open("a") as f:
        f.write(json.dumps(entry) + "\n")
    return entry


def read_log() -> list[dict]:
    if not AUDIT_LOG_PATH.exists():
        return []
    with AUDIT_LOG_PATH.open() as f:
        return [json.loads(line) for line in f if line.strip()]
