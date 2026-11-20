"""Read-only operating telemetry for the control room UI."""
from fastapi import APIRouter

from app.config import RAZORPAY_KEY_ID, resolve_provider
from app.stats.service import compute_stats, guardrail_config

router = APIRouter()


@router.get("/stats")
def stats():
    return compute_stats()


@router.get("/guardrails/config")
def guardrails():
    return guardrail_config()


@router.get("/mode")
def mode():
    """
    What the system is actually wired to right now. Surfaced in the UI so a
    demo never misrepresents itself: it says plainly whether orders are hitting
    Razorpay test mode or being mocked, and which brain is deciding.
    """
    live = bool(RAZORPAY_KEY_ID)
    return {
        "razorpay": "test_api" if live else "mock",
        "razorpay_key_id": RAZORPAY_KEY_ID if live else None,
        "agent_brain": resolve_provider(),
    }
