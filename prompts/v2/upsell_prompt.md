# Prompt Evolution — Version 2 (Candidate Bounded & Basic JSON)

## Overview & Context
**Version 2** addressed inventory hallucination and parseability. The candidate set was strictly derived from the base product's verified complementary items (`pairs_with`), and the prompt instructed the LLM to reply in a JSON structure.

---

## Prompt Definition

### System Prompt
```
You are an upsell recommendation engine for an e-commerce merchant. 
You will be provided a base product and a list of valid candidate add-on products currently in stock.
You must select at most ONE add-on from the provided list, or decide not to upsell.

Respond in JSON format with the following keys:
- "action": "offer_bundle" or "no_action"
- "addon_product_id": the id of the chosen product, or null
- "discount_percent": integer discount to offer
- "reasoning": why this product was chosen
```

### User Prompt Template
```
Base product: {base_name} (id={base_id}, price=₹{base_price})
Current cart total: ₹{cart_total}

Allowed add-on candidates:
- {candidate_1_id}: {candidate_1_name} (₹{candidate_1_price})
- {candidate_2_id}: {candidate_2_name} (₹{candidate_2_price})

Select the best upsell option.
```

---

## Sample LLM Output

```json
```json
{
  "action": "offer_bundle",
  "addon_product_id": "p2",
  "discount_percent": 25,
  "reasoning": "The silicone case cover provides essential drop protection for the earbuds, and a 25% discount will strongly motivate the buyer."
}
```
```

---

## Observed Vulnerabilities & Failure Modes

1. **Markdown Formatting Wrapping (` ```json ... ``` `):**
   - The LLM wrapped its JSON response in markdown code blocks. Standard `json.loads()` threw JSONDecodeErrors unless defensive regex stripping was implemented in code.

2. **Excessive Discount Proposals:**
   - Although candidate products were properly bounded, the model still suggested discounts above safety limits (e.g., 20% - 25%). 
   - While downstream guardrails blocked these, high rejection rates caused legitimate sales opportunities to stall in review queues rather than auto-executing.

3. **Absence of Confidence Metric:**
   - The engine still lacked a quantitative confidence score. Low-conviction matches (such as a generic accessory paired with a high-end keyboard) could not be programmatically differentiated from near-certain matches.

4. **Ambiguity on `no_action`:**
   - When no candidates fit, models sometimes returned `"addon_product_id": ""` or omitted the key entirely instead of sending `null`.

---

## Key Takeaways for Version 3
- Explicitly enforce the discount range (`0-15`) within the prompt itself.
- Introduce a standardized `confidence` float (`0.0` to `1.0`) to feed directly into deterministic guardrail gates.
- Specify exact schema types and disallow any conversational preamble or trailing text.
