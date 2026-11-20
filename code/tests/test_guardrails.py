"""Guardrails are deterministic, so they get exact unit tests. This is the
suite to show a judge for 'Safety & Control'."""
from app.guardrails.checks import (
    evaluate_action, validate_payload, add_to_daily_total,
    MAX_TRANSACTION_PAISE_AUTO, MIN_CONFIDENCE_AUTO,
)


def test_within_limits_auto_approves():
    r = evaluate_action(discount_percent=10, transaction_amount_paise=200_000, confidence=0.9)
    assert r.approved and not r.requires_human


def test_high_discount_needs_human():
    r = evaluate_action(discount_percent=40, transaction_amount_paise=200_000, confidence=0.9)
    assert not r.approved and r.requires_human
    assert "Discount" in r.reason


def test_over_transaction_cap_needs_human():
    r = evaluate_action(discount_percent=5,
                        transaction_amount_paise=MAX_TRANSACTION_PAISE_AUTO + 1, confidence=0.9)
    assert r.requires_human


def test_low_confidence_needs_human():
    r = evaluate_action(discount_percent=5, transaction_amount_paise=100_000,
                        confidence=MIN_CONFIDENCE_AUTO - 0.01)
    assert r.requires_human


def test_daily_cap_accumulates():
    add_to_daily_total(1_950_000)  # near the ₹20,000 daily cap
    r = evaluate_action(discount_percent=5, transaction_amount_paise=100_000, confidence=0.9)
    assert r.requires_human and "daily total" in r.reason


def test_payload_validation():
    assert validate_payload("p1", 1)[0] is True
    assert validate_payload("", 1)[0] is False
    assert validate_payload("p1", 0)[0] is False
    assert validate_payload("p1", -3)[0] is False
