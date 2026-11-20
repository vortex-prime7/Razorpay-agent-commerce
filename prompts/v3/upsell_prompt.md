# Prompt Evolution — Version 3 (Schema Enforcement & Confidence Scoring)

## Overview & Context
**Version 3** introduced strict schema constraints, numerical range limits for discounts (0–15%), and a calibrated confidence score (`0.0 - 1.0`). This allowed the downstream guardrail system to use both financial metrics and model confidence to decide between auto-execution and human review.

---

## Prompt Definition

### System Prompt
```
You are an upsell decision engine for an e-commerce merchant.
Given a base product and its allowed add-on candidates, decide whether to offer a bundle.
You may ONLY choose an add-on from the provided candidate ids.
You must respond with STRICT JSON and no other text, markdown formatting, or preamble.

Required JSON shape:
{
  "action": "offer_bundle" | "no_action",
  "addon_product_id": string | null,
  "discount_percent": integer between 0 and 15,
  "confidence": number between 0.0 and 1.0,
  "reasoning": string (max 200 characters)
}
```

### User Prompt Template
```
Base product: {base.name} (id={base_id}, ₹{base.price_paise / 100:.2f})
Cart total: ₹{cart_total_paise / 100:.2f}
Allowed add-on candidates:
- {candidate_id}: {candidate_name} (₹{candidate_price})

Decide the best single upsell, or no_action if none is worthwhile.
```

---

## Sample LLM Output

```json
{
  "action": "offer_bundle",
  "addon_product_id": "p2",
  "discount_percent": 10,
  "confidence": 0.88,
  "reasoning": "Protective case directly complements earbuds and cart value supports a modest 10% bundle incentive."
}
```

---

## Refinements Identified Before Final Release

1. **Occasional Markdown Code Block Encapsulation:**
   - Even when prompted with "no markdown formatting", models (especially across different model updates or temperatures) occasionally output ` ```json ` fences.
   - **Resolution:** Add defensive parsing in Python to strip markdown tags before calling `json.loads()`.

2. **Defense-in-Depth Whitelist Verification:**
   - While the prompt forbids picking unlisted IDs, an adversarial or corrupted model output could still emit an invalid ID.
   - **Resolution:** Python validation must assert `addon in candidates` and raise an exception if violated.

3. **Discount Clamping & Boundary Assertion:**
   - Never rely solely on LLM compliance with the 0–15% limit.
   - **Resolution:** Clamp discounts using `max(0, min(discount, MAX_DISCOUNT_PERCENT_AUTO))` in Python.

4. **Catch-All Exception Fallback:**
   - If the API provider drops, rate-limits, or raises a schema validation error, checkout must not abort.
   - **Resolution:** Route seamlessly to the deterministic offline rule engine.
