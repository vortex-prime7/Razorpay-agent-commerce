# Production Upsell Prompt (Final System Implementation)

## Overview & Location
This document defines the exact prompt and validation logic active in the production codebase at:
`code/app/agent/llm.py` and `code/app/agent/decision.py`.

The prompt is deliberately constrained: **the LLM handles contextual judgment, while pure deterministic code handles money, permissions, and execution.**

---

## Exact Production Prompts

### System Prompt (`SYSTEM_PROMPT` in `app/agent/llm.py`)
```text
You are an upsell decision engine for an e-commerce merchant. Given a base product and its allowed add-on candidates, decide whether to offer a bundle. You may ONLY choose an add-on from the provided candidate ids. Respond with STRICT JSON and nothing else, in this exact shape:
{"action": "offer_bundle" | "no_action", "addon_product_id": string | null, "discount_percent": integer 0-15, "confidence": number 0-1, "reasoning": string}
```

### User Prompt Construction (`_build_user_prompt` in `app/agent/llm.py`)
```python
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
```

---

## Output Contract & Schema

| Field | Type | Description | Strict Bounds |
|---|---|---|---|
| `action` | `string` | Upsell action proposed | `"offer_bundle"` or `"no_action"` |
| `addon_product_id` | `string \| null` | Selected candidate ID | Must exist in `candidates` (`pairs_with`); `null` if no action |
| `discount_percent` | `integer` | Recommended discount percentage | `0` to `15` |
| `confidence` | `float` | Model confidence in recommendation | `0.0` to `1.0` (auto-executes only if `≥ 0.75`) |
| `reasoning` | `string` | Human-readable explanation for audit log | Clamped to 300 characters |

---

## Defensive Python Validation Layer (`anthropic_decision`)

Before any LLM output is trusted near financial calculations, `app/agent/llm.py` performs strict multi-stage validation:

```python
# 1. Clean markdown code fences defensively
raw = "".join(block.text for block in resp.content if block.type == "text").strip()
raw = raw.replace("```json", "").replace("```", "").strip()
data = json.loads(raw)  # Raises JSONDecodeError if invalid -> caught by fallback

# 2. Extract and cast types
action = data.get("action")
addon = data.get("addon_product_id")
discount = int(data.get("discount_percent", 0))
confidence = float(data.get("confidence", 0))
reasoning = str(data.get("reasoning", ""))[:300]

# 3. Whitelist enforcement: Reject any product not in candidate list
if action == "offer_bundle":
    if addon not in candidates:
        raise ValueError(f"LLM chose add-on '{addon}' not in allowed candidates {candidates}")
    # 4. Enforce strict cap regardless of LLM claim
    discount = max(0, min(discount, MAX_DISCOUNT_PERCENT_AUTO))
else:
    action, addon, discount = "no_action", None, 0

# 5. Bound confidence
confidence = max(0.0, min(confidence, 1.0))
```

---

## Deterministic Fallback & Zero-Downtime Guarantee

If Claude encounters any failure (network drop, API outage, rate limit, JSON syntax error, or whitelist violation), `app/agent/decision.py` catches the exception and immediately invokes the offline deterministic rule engine:

```python
def decide(cart_total_paise: int, base_product_id: str) -> AgentDecision:
    provider = resolve_provider()
    if provider == "anthropic":
        try:
            from app.agent.llm import anthropic_decision
            return anthropic_decision(cart_total_paise, base_product_id)
        except Exception:
            # Graceful degradation: never break checkout if the model fails
            fallback = _offline_decision(cart_total_paise, base_product_id)
            fallback.reasoning = "[LLM unavailable, used deterministic fallback] " + fallback.reasoning
            return fallback
    return _offline_decision(cart_total_paise, base_product_id)
```

This guarantees **100% checkout uptime** even in total LLM outages.
