# Changelog

All notable changes to the **Agent Commerce Layer** project are documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/), and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

---

## [1.0.0] - Production Milestone 2 Release - 2026-11-20

### Added
- **Client Idempotency Spine:** Implemented `idempotency_key` support in `orchestrator/checkout.py`. Replaying identical idempotency keys returns stored results without triggering subsequent payment charges or order duplicates.
- **Payment Failure Recovery & Exponential Retry:** Bounded retry logic (`MAX_RETRIES=2`, exponential backoff) in `razorpay_client/client.py`.
- **Fail-to-Human Payment Routing:** In the event of persistent payment gateway exhaustion, the system guarantees zero charges are created and automatically routes the transaction to the human review queue with reason `Payment provider unavailable`.
- **Append-Only Audit Ledger:** Complete persistent audit trail (`audit/logger.py`) recording all checkout attempts, model proposals, guardrail decisions, execution results, and human reviewer actions.
- **Interactive Merchant Dashboard:** Live control room at `/dashboard` featuring real-time budget telemetry gauges, catalog viewer, human approval queue actions (Approve/Reject), interactive scenario triggers, and real-time activity stream.
- **End-to-End Test Suite:** Pytest coverage across guardrail limits, idempotent replays, failure recovery, and brain fallback workflows in `tests/`.

### Changed
- Standardized currency values as exact integer paise (`price_paise`, `amount_paise`) across catalog, agent decision, guardrails, and Razorpay API payloads to prevent floating-point rounding errors.
- Separated LLM reasoning dependencies so the application boots and operates seamlessly even when `anthropic` is not installed or when no API keys are configured.

---

## [0.9.0] - Deterministic Guardrails & Human-in-the-Loop Queue - 2026-11-15

### Added
- **Deterministic Guardrails Engine (`guardrails/checks.py`):** Pure Python rule engine executing completely independently of LLMs.
  - Discount ceiling auto-cap: `≤ 15%`.
  - Per-transaction spend auto-cap: `≤ ₹5,000` (500,000 paise).
  - Cumulative daily spend auto-cap: `≤ ₹20,000` (2,000,000 paise).
  - Minimum agent confidence threshold: `≥ 0.75`.
- **Persistent Daily Spend Tracking:** File-backed cumulative daily total (`data/daily_totals.json`) that survives server restarts.
- **Human-in-the-Loop Review Queue (`approvals/queue.py`):** Staging store for transactions exceeding auto-approval ceilings or failing confidence checks.
- **Approval Queue API Endpoints:** Added `GET /approvals/`, `POST /approvals/{id}/approve`, and `POST /approvals/{id}/reject`.
- **Payload Sanitization:** Immediate rejection of negative/zero quantities and non-string product IDs prior to spending evaluation.

### Changed
- Refactored checkout orchestrator to route out-of-bound proposals to `status: "pending_human_approval"` rather than failing or dropping customer transactions.

---

## [0.7.0] - LLM Upsell Agent & Prompt Hardening - 2026-11-08

### Added
- **Anthropic Claude Integration (`agent/llm.py`):** Integrated Claude 3.5 Haiku as the dynamic upsell proposal brain.
- **Strict Output Schema Enforcement:** Prompt engineered for rigid JSON output containing `action`, `addon_product_id`, `discount_percent`, `confidence`, and `reasoning`.
- **Defensive Post-Processing Validation:**
  - Whitelist candidate verification: rejects any add-on ID not explicitly listed in the base product's `pairs_with` array.
  - Automatic discount clamping to maximum auto-approval limit.
  - Confidence clamping between `0.0` and `1.0`.
- **Graceful Brain Fallback:** Automatic catch-all error handling in `agent/decision.py` that falls back to the offline rule engine if Claude times out or returns malformed JSON.

---

## [0.5.0] - Basket Intelligence & Offline Upsell Brain - 2026-10-30

### Added
- **Catalog Complementary Mapping:** Added `pairs_with` relationships to catalog product definitions in `catalog/data.py` (e.g., Wireless Earbuds pairing with Silicone Case Cover).
- **Deterministic Offline Brain (`_offline_decision`):** Baseline rule engine recommending standard 10% bundle discounts on qualifying cart totals (> ₹500) with complementary inventory.
- **Decision Dataclass (`AgentDecision`):** Standardized data contract between proposal brain and orchestrator.
- **Initial Activity Logging:** Rudimentary event capture for checkout attempts and decisions.

---

## [0.3.0] - Machine-Readable Surfaces & MCP Integration - 2026-10-18

### Added
- **schema.org JSON-LD Feed (`/catalog/agent-feed`):** Machine-native product catalog feed formatted for autonomous AI web buyers without HTML scraping.
- **Real-Time Stock Availability Endpoint (`/catalog/products/{id}/availability`):** Stock verification endpoint for shopping agents.
- **Model Context Protocol (MCP) Server (`mcp_server/server.py`):** Exposed catalog browsing, availability checks, and checkout initiation as callable MCP tools for AI agents.
- **Autonomous Buyer Agent Demonstration (`demo/buyer_agent.py`):** Reference Python script showcasing an autonomous agent reading the JSON-LD feed and executing a purchase.

---

## [0.1.0] - Initial Prototype - 2026-10-05

### Added
- Initial project scaffold with FastAPI application and Uvicorn server.
- In-memory product catalog models (`Product`) with IDs, names, pricing in paise, stock, and categories.
- Core checkout endpoint (`POST /checkout`) with base product and quantity selection.
- Isolated Razorpay client wrapper (`razorpay_client/client.py`) supporting both live test-mode API keys and zero-config mock orders.
