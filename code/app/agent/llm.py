"""
The Claude-backed brain. It is deliberately narrow: it only chooses among
*existing* paired products and returns a confidence + reasoning. We validate
its output hard — an LLM proposing an unknown product id, a silly discount,
or malformed JSON must never reach the payment path.

Kept separate from decision.py so the app runs with zero LLM dependencies
installed; this module is imported lazily only when a provider is active.
"""
import json

from app.agent.decision import AgentDecision
from app.catalog.data import PRODUCT_INDEX
from app.config import ANTHROPIC_API_KEY, LLM_MODEL
from app.guardrails.checks import MAX_DISCOUNT_PERCENT_AUTO

SYSTEM_PROMPT = (
    "You are an upsell decision engine for an e-commerce merchant. "
    "Given a base product and its allowed add-on candidates, decide whether to "
    "offer a bundle. You may ONLY choose an add-on from the provided candidate "
    "ids. Respond with STRICT JSON and nothing else, in this exact shape:\n"
    '{"action": "offer_bundle" | "no_action", "addon_product_id": string | null, '
    '"discount_percent": integer 0-15, "confidence": number 0-1, "reasoning": string}'
)


def _build_user_prompt(cart_total_paise: int, base_id: str, candidates: list[str]) -> str:
    base = PRODUCT_INDEX[base_id]
    cand_lines = [
        f'- {cid}: {PRODUCT_INDEX[cid].name} (₹{PRODUCT_INDEX[cid].price_paise/100:.2f})'
        for cid in candidates if cid in PRODUCT_INDEX
    ]
    return (
        f"Base product: {base.name} (id={base_id}, ₹{base.price_paise/100:.2f})\n"
        f"Cart total: ₹{cart_total_paise/100:.2f}\n"
        f"Allowed add-on candidates:\n" + ("\n".join(cand_lines) or "(none)") +
        "\n\nDecide the best single upsell, or no_action if none is worthwhile."
    )


def anthropic_decision(cart_total_paise: int, base_product_id: str) -> AgentDecision:
    import anthropic  # lazy import

    base = PRODUCT_INDEX.get(base_product_id)
    candidates = base.pairs_with if base else []

    client = anthropic.Anthropic(api_key=ANTHROPIC_API_KEY)
    resp = client.messages.create(
        model=LLM_MODEL,
        max_tokens=300,
        system=SYSTEM_PROMPT,
        messages=[{"role": "user",
                   "content": _build_user_prompt(cart_total_paise, base_product_id, candidates)}],
    )
    raw = "".join(block.text for block in resp.content if block.type == "text").strip()
    raw = raw.replace("```json", "").replace("```", "").strip()
    data = json.loads(raw)  # may raise -> caught by decide()'s fallback

    # --- Validate the model's output before trusting it anywhere near money.
    action = data.get("action")
    addon = data.get("addon_product_id")
    discount = int(data.get("discount_percent", 0))
    confidence = float(data.get("confidence", 0))
    reasoning = str(data.get("reasoning", ""))[:300]

    if action == "offer_bundle":
        if addon not in candidates:
            raise ValueError(f"LLM chose add-on '{addon}' not in allowed candidates {candidates}")
        discount = max(0, min(discount, MAX_DISCOUNT_PERCENT_AUTO))  # clamp, never trust blindly
    else:
        action, addon, discount = "no_action", None, 0
    confidence = max(0.0, min(confidence, 1.0))

    return AgentDecision(
        action=action,
        base_product_id=base_product_id,
        addon_product_id=addon,
        discount_percent=discount,
        confidence=confidence,
        reasoning=reasoning or "(no reasoning returned)",
        provider="anthropic",
    )
