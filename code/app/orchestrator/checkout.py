"""
The spine. One function, `checkout`, walks a purchase through every layer in
order and records what happened at each step:

    catalog  ->  agent (propose upsell)  ->  guardrails (permit?)
             ->  either auto-execute via Razorpay, or queue for a human
             ->  audit log (always)

Two safety properties are enforced here, and they're the ones to explain at
the panel:
  * Idempotency: the same idempotency_key never creates a second order, so a
    client retry after a timeout cannot double-charge.
  * Fail-to-human: if the Razorpay call is exhausted, no order exists (so no
    charge happened) and the purchase is routed to human review — never
    silently dropped, never blind-retried forever.
"""
import json

from app.catalog.data import PRODUCT_INDEX
from app.agent.decision import decide
from app.guardrails.checks import (
    evaluate_action,
    validate_payload,
    add_to_daily_total,
)
from app.razorpay_client import client as rzp
from app.audit.logger import log_event
from app.approvals import queue
from app.config import IDEMPOTENCY_PATH
from app.orchestrator.models import CheckoutResult


# --- Idempotency store: idempotency_key -> completed result dict.
def _load_idem() -> dict:
    if IDEMPOTENCY_PATH.exists():
        return json.loads(IDEMPOTENCY_PATH.read_text())
    return {}


def _remember_idem(key: str, result: dict) -> None:
    store = _load_idem()
    store[key] = result
    IDEMPOTENCY_PATH.write_text(json.dumps(store, indent=2))


def _price(product_id: str) -> int:
    return PRODUCT_INDEX[product_id].price_paise


def _execute_order(amount_paise: int, notes: dict) -> tuple[bool, str | None, str]:
    """
    Attempt the actual Razorpay test-mode order (retry/backoff lives in the
    client). Returns (success, order_id, message). On failure NO order was
    created, so the caller can safely route to a human without risk of a
    duplicate charge.
    """
    try:
        order = rzp.create_order(amount_paise, notes=notes)
        return True, order.get("id"), "Order created in Razorpay test mode"
    except rzp.RazorpayUnavailable as e:
        return False, None, str(e)


def checkout(base_product_id: str, quantity: int, idempotency_key: str) -> CheckoutResult:
    # 0) Idempotent replay — a repeated key returns the first result, no new charge.
    prior = _load_idem().get(idempotency_key)
    if prior:
        log_event(
            event="checkout_replay",
            reasoning="Idempotency key already processed; returning stored result.",
            guardrail_result="n/a",
            outcome="replayed",
            extra={"idempotency_key": idempotency_key},
        )
        replayed = CheckoutResult(**prior)
        replayed.status = "replayed"
        replayed.message = "Idempotent replay — no new charge created."
        return replayed

    # 1) Validate payload (invalid-payload failure mode).
    ok, msg = validate_payload(base_product_id, quantity)
    if not ok or base_product_id not in PRODUCT_INDEX:
        detail = msg if not ok else f"Unknown product '{base_product_id}'"
        entry = log_event("checkout_attempt", "Payload rejected before any spend.",
                          guardrail_result=detail, outcome="failed")
        return CheckoutResult(status="failed", message=detail, audit_id=entry["id"])

    base_total = _price(base_product_id) * quantity

    # 2) Agent proposes an upsell (LLM or offline). No money touched yet.
    decision = decide(base_total, base_product_id)

    upsell = decision.action == "offer_bundle" and decision.addon_product_id
    if upsell:
        addon_price = _price(decision.addon_product_id)
        discounted_addon = round(addon_price * (100 - decision.discount_percent) / 100)
        txn_amount = base_total + discounted_addon
    else:
        txn_amount = base_total

    # 3) Guardrails decide: auto-execute or human-gate. (Deterministic.)
    gr = evaluate_action(
        discount_percent=decision.discount_percent,
        transaction_amount_paise=txn_amount,
        confidence=decision.confidence,
    )

    notes = {
        "base_product": base_product_id,
        "quantity": str(quantity),
        "upsell": decision.addon_product_id or "none",
        "discount_percent": str(decision.discount_percent),
        "idempotency_key": idempotency_key,
    }

    # 4a) Auto-approved -> execute now.
    if gr.approved:
        success, order_id, exec_msg = _execute_order(txn_amount, notes)
        if success:
            add_to_daily_total(txn_amount)
            result = CheckoutResult(
                status="completed", message=exec_msg, order_id=order_id,
                amount_paise=txn_amount, upsell_offered=bool(upsell),
                addon_product_id=decision.addon_product_id,
                discount_percent=decision.discount_percent,
                agent_confidence=decision.confidence, agent_provider=decision.provider,
            )
            entry = log_event(
                "checkout_completed",
                reasoning=decision.reasoning,
                guardrail_result=gr.reason,
                outcome="auto_executed",
                provider=decision.provider,
                extra={"order_id": order_id, "amount_paise": txn_amount, "notes": notes},
            )
            result.audit_id = entry["id"]
            _remember_idem(idempotency_key, result.model_dump())
            return result

        # 4a-fail) Razorpay exhausted -> no charge happened -> route to human.
        item = queue.enqueue(
            payload={"base_product_id": base_product_id, "quantity": quantity,
                     "amount_paise": txn_amount, "notes": notes,
                     "idempotency_key": idempotency_key},
            reason=f"Payment provider unavailable: {exec_msg}",
        )
        entry = log_event(
            "checkout_failed",
            reasoning=decision.reasoning,
            guardrail_result=f"{gr.reason}; payment provider then failed after retries "
                             f"-> routed to human review (no charge made)",
            outcome="failed_routed_to_human",
            provider=decision.provider,
            extra={"error": exec_msg, "approval_id": item["id"], "amount_paise": txn_amount},
        )
        return CheckoutResult(
            status="failed",
            message=f"Payment failed after retries; routed to human review. No charge was made. ({exec_msg})",
            amount_paise=txn_amount, upsell_offered=bool(upsell),
            addon_product_id=decision.addon_product_id,
            discount_percent=decision.discount_percent,
            agent_confidence=decision.confidence, agent_provider=decision.provider,
            audit_id=entry["id"], approval_id=item["id"],
        )

    # 4b) Not auto-approved -> queue for a human, execute nothing.
    item = queue.enqueue(
        payload={"base_product_id": base_product_id, "quantity": quantity,
                 "amount_paise": txn_amount, "notes": notes,
                 "idempotency_key": idempotency_key},
        reason=gr.reason,
    )
    entry = log_event(
        "checkout_queued",
        reasoning=decision.reasoning,
        guardrail_result=gr.reason,
        outcome="queued_for_human",
        provider=decision.provider,
        extra={"approval_id": item["id"], "amount_paise": txn_amount, "notes": notes},
    )
    return CheckoutResult(
        status="pending_human_approval", message=gr.reason,
        amount_paise=txn_amount, upsell_offered=bool(upsell),
        addon_product_id=decision.addon_product_id,
        discount_percent=decision.discount_percent,
        agent_confidence=decision.confidence, agent_provider=decision.provider,
        audit_id=entry["id"], approval_id=item["id"],
    )


def approve(item_id: str) -> CheckoutResult:
    """Human approves a queued item -> execute the stored order now."""
    item = queue.get(item_id)
    if not item:
        return CheckoutResult(status="failed", message=f"Approval item '{item_id}' not found")
    if item["status"] != "pending":
        return CheckoutResult(status="failed", message=f"Item already {item['status']}")

    p = item["payload"]
    key = p.get("idempotency_key", item_id)
    prior = _load_idem().get(key)
    if prior:  # already executed via another path
        queue.set_status(item_id, "approved")
        return CheckoutResult(**prior)

    success, order_id, exec_msg = _execute_order(p["amount_paise"], p.get("notes", {}))
    if not success:
        log_event("approval_execute_failed", "Human approved; provider still failing.",
                  guardrail_result="human_approved", outcome="failed",
                  extra={"approval_id": item_id, "error": exec_msg})
        return CheckoutResult(status="failed",
                              message=f"Approved, but payment failed: {exec_msg}", approval_id=item_id)

    queue.set_status(item_id, "approved")
    add_to_daily_total(p["amount_paise"])
    result = CheckoutResult(status="completed", message="Human-approved and executed",
                            order_id=order_id, amount_paise=p["amount_paise"], approval_id=item_id)
    entry = log_event("approval_executed", "Human approved the queued action.",
                      guardrail_result="human_approved", outcome="human_approved_executed",
                      extra={"approval_id": item_id, "order_id": order_id,
                             "amount_paise": p["amount_paise"], "notes": p.get("notes", {})})
    result.audit_id = entry["id"]
    _remember_idem(key, result.model_dump())
    return result


def reject(item_id: str) -> CheckoutResult:
    item = queue.set_status(item_id, "rejected")
    if not item:
        return CheckoutResult(status="failed", message=f"Approval item '{item_id}' not found")
    log_event("approval_rejected", "Human rejected the queued action.",
              guardrail_result="human_rejected", outcome="rejected",
              extra={"approval_id": item_id})
    return CheckoutResult(status="failed", message="Rejected by human reviewer", approval_id=item_id)
