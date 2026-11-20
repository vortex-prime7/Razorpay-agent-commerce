"""End-to-end orchestrator tests: every outcome path a judge cares about —
auto-execute, human gate, invalid payload, persistent-failure -> human with no
double charge, and idempotent replay."""
import uuid

from app.orchestrator.checkout import checkout, approve
from app.razorpay_client import client as rzp


def _key():
    return "test_" + uuid.uuid4().hex[:10]


def test_small_purchase_auto_executes():
    r = checkout("p1", 1, _key())
    assert r.status == "completed"
    assert r.order_id and r.amount_paise > 0


def test_offline_agent_offers_upsell():
    r = checkout("p1", 1, _key())        # p1 pairs_with p2, cart > ₹500
    assert r.upsell_offered and r.addon_product_id == "p2"
    assert r.agent_provider == "offline"


def test_large_order_goes_to_human_queue():
    r = checkout("p3", 2, _key())        # 2x keyboard exceeds per-transaction cap
    assert r.status == "pending_human_approval"
    assert r.approval_id and r.order_id is None   # nothing charged yet


def test_invalid_product_fails_before_spend():
    r = checkout("does_not_exist", 1, _key())
    assert r.status == "failed" and r.order_id is None


def test_persistent_failure_routes_to_human_no_charge():
    rzp.FAIL_MODE = "always"             # every retry fails this checkout
    r = checkout("p1", 1, _key())
    assert r.status == "failed"
    assert r.order_id is None            # <-- no order created, so no double charge
    assert r.approval_id                 # routed to human review instead
    assert rzp.FAIL_MODE == "off"        # auto-reset for the next action


def test_idempotent_replay_does_not_double_charge():
    k = _key()
    first = checkout("p1", 1, k)
    second = checkout("p1", 1, k)        # same key -> must not create a new order
    assert first.status == "completed"
    assert second.status == "replayed"
    assert second.order_id == first.order_id


def test_human_approval_then_executes():
    queued = checkout("p3", 2, _key())   # -> pending
    assert queued.status == "pending_human_approval"
    done = approve(queued.approval_id)
    assert done.status == "completed" and done.order_id
