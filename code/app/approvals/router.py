"""HTTP surface for the human-in-the-loop approval queue."""
from fastapi import APIRouter

from app.approvals import queue
from app.orchestrator.checkout import approve, reject

router = APIRouter()


@router.get("/")
def list_approvals(status: str | None = None):
    """List queued items (optionally filter by status: pending/approved/rejected)."""
    return queue.list_items(status)


@router.post("/{item_id}/approve")
def approve_item(item_id: str):
    """Human approves a pending action -> it executes now."""
    return approve(item_id)


@router.post("/{item_id}/reject")
def reject_item(item_id: str):
    """Human rejects a pending action -> nothing executes."""
    return reject(item_id)
