"""HTTP surface for the checkout flow, plus a small demo control to arm the
simulated payment failure on command (used for the failure-recovery demo)."""
from fastapi import APIRouter

from app.orchestrator.checkout import checkout
from app.orchestrator.models import CheckoutRequest, CheckoutResult
from app.razorpay_client import client as rzp
from app.config import (
    AUDIT_LOG_PATH, APPROVAL_QUEUE_PATH, DAILY_TOTALS_PATH, IDEMPOTENCY_PATH,
)

router = APIRouter()


@router.post("/checkout", response_model=CheckoutResult)
def do_checkout(req: CheckoutRequest):
    """
    Entry point an autonomous buyer (or your app's checkout) calls. Returns a
    structured result describing exactly what happened and why.
    """
    return checkout(req.base_product_id, req.quantity, req.idempotency_key)


@router.post("/demo/arm-failure")
def arm_failure(mode: str = "always"):
    """
    Arm a simulated Razorpay failure for the next checkout:
      mode="always" (default): the payment fails through all retries, so the
        purchase is routed to human review with NO charge made — then behavior
        auto-resets to normal.
      mode="once": one transient failure that the retry/backoff recovers from.
    """
    rzp.FAIL_MODE = "once" if mode == "once" else "always"
    return {"armed": True, "mode": rzp.FAIL_MODE,
            "note": "Next checkout will hit a simulated payment failure."}


@router.post("/demo/reset")
def reset_demo():
    """
    Clear the audit log, approval queue, daily totals and idempotency store so
    a demo starts from a clean slate. Demo tooling only — a real deployment
    would never expose this.
    """
    for path in (AUDIT_LOG_PATH, APPROVAL_QUEUE_PATH, DAILY_TOTALS_PATH, IDEMPOTENCY_PATH):
        if path.exists():
            path.unlink()
    rzp.FAIL_MODE = "off"
    return {"reset": True}
