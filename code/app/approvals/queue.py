"""
Human-in-the-loop approval queue. Anything the guardrails won't auto-approve
lands here as 'pending' instead of being dropped or force-executed. A human
approves or rejects; only on approval does the transaction actually run.

This is the concrete implementation of "human-gated/permissioned" from the
brief. File-backed so the queue survives a restart mid-demo.
"""
import json
import uuid
from datetime import datetime, timezone

from app.config import APPROVAL_QUEUE_PATH


def _load() -> list[dict]:
    if APPROVAL_QUEUE_PATH.exists():
        return json.loads(APPROVAL_QUEUE_PATH.read_text())
    return []


def _save(items: list[dict]) -> None:
    APPROVAL_QUEUE_PATH.write_text(json.dumps(items, indent=2))


def enqueue(payload: dict, reason: str) -> dict:
    """Add a pending item awaiting human decision."""
    items = _load()
    item = {
        "id": str(uuid.uuid4()),
        "created_at": datetime.now(timezone.utc).isoformat(),
        "status": "pending",
        "reason": reason,        # why a human is needed (from the guardrail)
        "payload": payload,      # everything needed to execute if approved
        "decided_at": None,
    }
    items.append(item)
    _save(items)
    return item


def list_items(status: str | None = None) -> list[dict]:
    items = _load()
    if status:
        return [i for i in items if i["status"] == status]
    return items


def get(item_id: str) -> dict | None:
    return next((i for i in _load() if i["id"] == item_id), None)


def set_status(item_id: str, status: str) -> dict | None:
    items = _load()
    for i in items:
        if i["id"] == item_id:
            i["status"] = status
            i["decided_at"] = datetime.now(timezone.utc).isoformat()
            _save(items)
            return i
    return None
