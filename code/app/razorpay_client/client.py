"""
Isolated wrapper around Razorpay's test-mode API. Everything Razorpay-shaped
lives behind this boundary so:
  1. The rest of the app never imports razorpay directly.
  2. Failures can be simulated on command -> no real network needed to demo
     the failure-handling path.
  3. The app is runnable with ZERO setup: with no keys it returns a clearly
     labelled MOCK order; add real test keys and it hits real Razorpay.

For your actual submission, set RAZORPAY_KEY_ID / RAZORPAY_KEY_SECRET in .env
so orders show up in your Razorpay test dashboard.

Install: pip install razorpay   |   Docs: https://razorpay.com/docs/api/
"""
import time
import uuid

from app.config import (
    RAZORPAY_KEY_ID,
    RAZORPAY_KEY_SECRET,
    MAX_RETRIES,
    RETRY_BASE_DELAY_SEC,
)

# --- Demo failure switch:
#   "off"    -> normal behaviour
#   "once"   -> next single attempt fails, then recovers (transient; retry succeeds)
#   "always" -> every attempt in the current checkout fails (persistent; routes to human),
#               then auto-resets to "off" so the demo returns to normal
FAIL_MODE = "off"


class RazorpayUnavailable(Exception):
    """Raised when the Razorpay call fails after all retries are exhausted."""


def _real_client():
    import razorpay
    return razorpay.Client(auth=(RAZORPAY_KEY_ID, RAZORPAY_KEY_SECRET))


def _create_order_once(amount_paise: int, currency: str, notes: dict) -> dict:
    """One raw attempt. Honors the demo failure switch, then talks to Razorpay
    (or returns a labelled mock if no keys are configured)."""
    global FAIL_MODE
    if FAIL_MODE == "once":
        FAIL_MODE = "off"
        raise TimeoutError("Simulated transient Razorpay timeout (retry should recover)")
    if FAIL_MODE == "always":
        raise TimeoutError("Simulated persistent Razorpay outage (should route to human)")

    if RAZORPAY_KEY_ID and RAZORPAY_KEY_SECRET:
        return _real_client().order.create(
            {"amount": amount_paise, "currency": currency, "notes": notes or {}}
        )
    # No keys -> labelled mock so the whole flow is demoable with zero setup.
    return {
        "id": "order_mock_" + uuid.uuid4().hex[:12],
        "amount": amount_paise,
        "currency": currency,
        "status": "created",
        "notes": notes or {},
        "mock": True,
    }


def create_order(amount_paise: int, currency: str = "INR", notes: dict | None = None) -> dict:
    """
    Create a test-mode order with bounded retry + exponential backoff.
    Raises RazorpayUnavailable if every attempt fails — the caller (the
    orchestrator) decides what to do then (route to a human). We never
    silently swallow the error and never blind-retry forever.
    """
    global FAIL_MODE
    attempts = MAX_RETRIES + 1
    last_error: Exception | None = None
    try:
        for i in range(attempts):
            try:
                return _create_order_once(amount_paise, currency, notes or {})
            except Exception as e:  # noqa: BLE001 - deliberate: retry with backoff
                last_error = e
                if i < attempts - 1:
                    time.sleep(RETRY_BASE_DELAY_SEC * (2 ** i))  # 0.5s, 1s, 2s, ...
        raise RazorpayUnavailable(
            f"Razorpay order failed after {attempts} attempts: {last_error}"
        )
    finally:
        # A persistent-outage demo is one-shot: fail this whole checkout, then
        # return to normal so the next action succeeds.
        if FAIL_MODE == "always":
            FAIL_MODE = "off"
