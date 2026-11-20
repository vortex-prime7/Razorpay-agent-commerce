# Prompt Evolution — Version 1 (Naive Open-Ended Assistant)

## Overview & Context
In **Version 1**, the objective was to test whether an LLM could act as an intuitive e-commerce upselling agent. The prompt relied entirely on natural language instructions without structured output constraints or candidate restrictions.

---

## Prompt Definition

### System Prompt
```
You are an expert e-commerce sales assistant. When a customer adds an item to their cart, your job is to suggest a complementary product to upsell and recommend an attractive discount to incentivize them to complete the purchase. Be persuasive, helpful, and friendly.
```

### User Prompt Template
```
The customer is purchasing: {base_product_name} priced at ₹{price}.
Cart total: ₹{cart_total}.

What product should we offer them as an add-on, what discount should we give, and why?
```

---

## Sample LLM Output

```
That's a great choice! Since the customer is buying the Wireless Earbuds for ₹2,499.00, they would definitely appreciate a High-Speed Wireless Charging Pad or Premium Foam Ear Tips! 

I recommend offering the Wireless Charging Pad at a special 35% bundle discount. 

Reasoning: Wireless earbuds require frequent charging, and offering a substantial 35% discount creates strong urgency and increases average order value significantly!
```

---

## Observed Vulnerabilities & Failure Modes

1. **Hallucination of Inventory:**
   - The LLM suggested products ("High-Speed Wireless Charging Pad", "Premium Foam Ear Tips") that did not exist in the merchant's physical catalog.
   - Result: Immediate checkout crashes when attempting to look up non-existent SKUs in the catalog.

2. **Unbounded Financial Risk:**
   - The LLM recommended a **35% discount**, far above merchant gross margin thresholds.
   - Without hard boundaries, the agent was freely giving away merchant revenue.

3. **Unparseable Free-Text Output:**
   - The response was conversational prose with markdown styling.
   - Automated checkout pipelines cannot reliably extract product IDs, discount percentages, or decisions from arbitrary natural language without brittle regex or another expensive LLM call.

4. **Zero Measure of Certainty:**
   - No confidence scoring existed, making it impossible to separate high-conviction complementary matches from wild guesses.

---

## Key Takeaways for Version 2
- Restrict the model's decision space strictly to valid in-stock candidate product IDs (`pairs_with`).
- Mandate JSON formatting so downstream services can consume the decision programmatically.
