# Spec — Bounded Upsell Agent + Agent-Readable Catalog

## Problem
Two real merchant gaps, one system:
1. **Sales growth:** carts convert below potential because there's no smart,
   real-time upsell at checkout.
2. **AI-to-AI shopping:** stores are built for human eyes (HTML), so
   autonomous AI buyers can't reliably read or transact against them.

## What it does
- Exposes the merchant catalog as an **agent-readable** interface: a
  schema.org **JSON-LD feed** (REST) and an **MCP server** with the same
  data as callable tools.
- At checkout, an **upsell agent** proposes a bundle. The proposal is bounded
  by deterministic **guardrails** before any money moves. In-budget,
  high-confidence actions auto-execute; anything else is **human-gated**.
- Every action is written to an append-only **audit trail**.

## The AI / not-AI split (deliberate)
- **LLM decides:** which add-on to offer, discount within a hard ceiling, a
  confidence score, and a one-line rationale.
- **Plain code decides:** all money math, every cap, payload validation, and
  whether a transaction may execute. No LLM output is ever trusted unchecked —
  unknown product ids are rejected, discounts are clamped.

## Caps (guardrails)
| Rule | Auto-approve limit |
|------|--------------------|
| Discount | ≤ 15% |
| Per-transaction | ≤ ₹5,000 |
| Daily cumulative | ≤ ₹20,000 |
| Agent confidence | ≥ 0.75 |

Any breach → routed to the human approval queue (never dropped, never forced).

## Failure modes handled
1. **Invalid payload** — rejected before any spend.
2. **Budget/cap hit** — routed to human approval.
3. **Payment API drop** — bounded retry + exponential backoff; if exhausted,
   no order is created (so **no double charge**) and the purchase is routed to
   a human. Transient drops recover on retry.
4. **LLM unavailable** — agent degrades to the deterministic brain.

## Safety property to call out
**Idempotency:** each purchase carries an idempotency key; a repeated key
returns the original result instead of creating a second order. A client that
retries after a timeout cannot double-charge.
