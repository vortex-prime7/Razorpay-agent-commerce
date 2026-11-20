"""
Live operating metrics, computed from the audit log rather than stored
separately — the log is the source of truth, so the numbers can never drift
out of sync with what actually happened.
"""
from app.audit.logger import read_log
from app.guardrails import checks

EXECUTED = {"auto_executed", "human_approved_executed"}


def compute_stats() -> dict:
    log = read_log()

    executed = [e for e in log if e["outcome"] in EXECUTED]
    held = [e for e in log if e["outcome"] == "queued_for_human"]
    failed = [e for e in log if e["outcome"] in ("failed", "failed_routed_to_human")]

    gmv = sum(e.get("extra", {}).get("amount_paise", 0) for e in executed)

    # Upsell attach rate across completed checkouts that ran the agent.
    checkouts = [e for e in log if e["event"] in ("checkout_completed", "checkout_queued")]
    with_upsell = [e for e in checkouts if e.get("extra", {}).get("notes", {}).get("upsell", "none") != "none"]
    attach_rate = (len(with_upsell) / len(checkouts)) if checkouts else 0.0

    decided = len(executed) + len(held)
    auto_rate = (len(executed) / decided) if decided else 0.0

    daily_spent = checks.get_daily_total_paise()

    return {
        "orders_placed": len(executed),
        "held_for_approval": len(held),
        "failures_handled": len(failed),
        "gmv_paise": gmv,
        "upsell_attach_rate": round(attach_rate, 3),
        "auto_approval_rate": round(auto_rate, 3),
        "daily_spent_paise": daily_spent,
        "daily_cap_paise": checks.MAX_DAILY_TOTAL_PAISE_AUTO,
        "daily_remaining_paise": max(0, checks.MAX_DAILY_TOTAL_PAISE_AUTO - daily_spent),
        "total_events": len(log),
    }


def guardrail_config() -> dict:
    """The caps currently in force — read by the UI so limits are never
    duplicated in two places."""
    return {
        "max_discount_percent": checks.MAX_DISCOUNT_PERCENT_AUTO,
        "max_transaction_paise": checks.MAX_TRANSACTION_PAISE_AUTO,
        "max_daily_total_paise": checks.MAX_DAILY_TOTAL_PAISE_AUTO,
        "min_confidence": checks.MIN_CONFIDENCE_AUTO,
    }
