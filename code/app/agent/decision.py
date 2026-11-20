"""
The upsell agent's PROPOSAL layer. It decides *which* upsell to suggest,
*how much* discount, and *how confident* it is — with a short reasoning
string. It never touches money; the guardrails have final say and the
orchestrator executes.

`decide()` is the single entry point. It routes to a provider (Claude or
the deterministic offline brain) and always returns the same shape, so
nothing downstream cares which brain answered.
"""
from dataclasses import dataclass

from app.catalog.data import PRODUCT_INDEX
from app.config import resolve_provider


@dataclass
class AgentDecision:
    action: str                 # "offer_bundle" | "no_action"
    base_product_id: str
    addon_product_id: str | None
    discount_percent: int
    confidence: float
    reasoning: str              # short, human-readable -> goes into the audit log
    provider: str               # which brain produced this ("anthropic" | "offline")


def _offline_decision(cart_total_paise: int, base_product_id: str) -> AgentDecision:
    """
    Deterministic rule-based brain. This is both the fallback AND a
    demonstration of "knowing when NOT to use an LLM": for a rule this
    simple, plain code is more reliable than a model. It also keeps a live
    demo working with no API key and no network.
    """
    base = PRODUCT_INDEX.get(base_product_id)
    candidates = base.pairs_with if base else []
    if cart_total_paise > 50_000 and candidates:  # > ₹500 and something to pair
        return AgentDecision(
            action="offer_bundle",
            base_product_id=base_product_id,
            addon_product_id=candidates[0],
            discount_percent=10,
            confidence=0.82,
            reasoning="Cart over ₹500 with a listed complementary item; standard 10% bundle offer.",
            provider="offline",
        )
    return AgentDecision(
        action="no_action",
        base_product_id=base_product_id,
        addon_product_id=None,
        discount_percent=0,
        confidence=1.0,
        reasoning="No qualifying upsell (cart below threshold or no paired item).",
        provider="offline",
    )


def decide(cart_total_paise: int, base_product_id: str) -> AgentDecision:
    """Route to the configured brain; always fall back to offline on any error."""
    provider = resolve_provider()
    if provider == "anthropic":
        try:
            from app.agent.llm import anthropic_decision
            return anthropic_decision(cart_total_paise, base_product_id)
        except Exception:
            # Graceful degradation: if the model call fails for ANY reason,
            # drop to the deterministic brain rather than break checkout.
            fallback = _offline_decision(cart_total_paise, base_product_id)
            fallback.reasoning = "[LLM unavailable, used deterministic fallback] " + fallback.reasoning
            return fallback
    return _offline_decision(cart_total_paise, base_product_id)
