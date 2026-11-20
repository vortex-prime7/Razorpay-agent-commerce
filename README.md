# Agent Commerce Layer

[![Track](https://img.shields.io/badge/Razorpay%20AI%20Buildathon-Track%2001-blue)](https://razorpay.com)
[![Python](https://img.shields.io/badge/Python-3.10%2B-brightgreen)](https://www.python.org/)
[![FastAPI](https://img.shields.io/badge/FastAPI-0.115%2B-009688)](https://fastapi.tiangolo.com)
[![Model Context Protocol](https://img.shields.io/badge/MCP-1.2%2B-orange)](https://modelcontextprotocol.io)

> A bounded **upsell agent** + an **agent-readable catalog**, built on Razorpay test-mode APIs. Grows merchant sales with intelligent, real-time basket additions while making the storefront natively discoverable and transactable for autonomous AI buyers — with every financial action strictly bounded, human-gated when needed, and immutably audited.

---

## Submission Details

- **Track:** Track 01 — Razorpay AI Buildathon
- **Team Name / Details:** `[Team Details / Member Names]`
- **Prototype / Live Demo Link:** `[Prototype / Demo Link]`
- **Repository:** Milestone 2 Directory Structure (`Razorpay-agent-commerce`)

---

## Executive Summary

Traditional e-commerce storefronts suffer from two compounding limitations:
1. **Human Cart Abandonment & Missed AOV:** Stores lack smart, context-aware upsell intelligence at checkout, missing out on high-intent basket additions.
2. **AI-to-AI Commerce Blindness:** Storefronts are styled for human visual rendering (HTML/CSS), making them fragile and unreadable for autonomous shopping agents.

The **Agent Commerce Layer** resolves both gaps through a clean separation of concerns:
- **LLM Intelligence for Judgment:** Claude (or a deterministic fallback) evaluates the cart context, complementary accessories, and customer intent to propose a bundle with confidence scoring and rationale.
- **Deterministic Code for Money & Permission:** Strict, hardcoded Python guardrails validate all inputs, enforce spend ceilings (discount %, transaction cap, daily budget), and control payment gateway interactions. The LLM never touches payment credentials or authorizes fund transfers directly.
- **Native AI-to-AI Interfaces:** Autonomous agents can consume products via schema.org JSON-LD (`/catalog/agent-feed`) or interact natively via Model Context Protocol (MCP) tools.

---

## Architecture Overview

```
                      ┌──────────────────────────────────────────────┐
                      │          Autonomous AI Buyer / Client        │
                      └──────────────────────┬───────────────────────┘
                                             │
                       ┌─────────────────────┴──────────────────────┐
                       │                                            │
                       ▼                                            ▼
           ┌───────────────────────┐                    ┌───────────────────────┐
           │ REST API & JSON-LD    │                    │  MCP Server (Tools)   │
           │ (/catalog/agent-feed) │                    │  (mcp_server/server)  │
           └───────────┬───────────┘                    └───────────┬───────────┘
                       │                                            │
                       └─────────────────────┬──────────────────────┘
                                             │
                                             ▼
                       ┌────────────────────────────────────────────┐
                       │         orchestrator/checkout.py           │
                       │    (Spine: Idempotency & Orchestration)    │
                       └───────┬──────────────┬──────────────┬──────┘
                               │              │              │
             ┌─────────────────┘              │              └─────────────────┐
             ▼                                ▼                                ▼
┌─────────────────────────┐      ┌─────────────────────────┐      ┌─────────────────────────┐
│     catalog/data.py     │      │     agent/decision.py   │      │   guardrails/checks.py  │
│  In-memory store &      │      │  LLM Proposal Brain     │      │  Deterministic Caps &   │
│  JSON-LD serialization  │      │  (Claude / Fallback)    │      │  Auto-Approve Engine    │
└─────────────────────────┘      └────────────┬────────────┘      └────────────┬────────────┘
                                              │                                │
                                              │ Proposal                       │ Pass / Breach
                                              ▼                                ▼
                                 ┌──────────────────────────────────────────────────────────┐
                                 │ Decision Router: Within Caps & Confident (≥0.75)?        │
                                 └────────────┬─────────────────────────────┬───────────────┘
                                              │ YES                         │ NO
                                              ▼                             ▼
                                 ┌─────────────────────────┐   ┌────────────────────────────┐
                                 │   razorpay_client/      │   │     approvals/queue.py     │
                                 │   Test-Mode Gateway     │   │ Human-in-the-Loop Review   │
                                 │   + Exponential Retry   │   │ Queue (Approve / Reject)   │
                                 └────────────┬────────────┘   └────────────┬───────────────┘
                                              │                             │
                                              └──────────────┬──────────────┘
                                                             │
                                                             ▼
                                               ┌────────────────────────────┐
                                               │      audit/logger.py       │
                                               │ Append-Only Audit Trail    │
                                               └────────────────────────────┘
```

### The AI / Plain-Code Separation Principle

| Component | Responsibility | Technology |
|---|---|---|
| **Proposal Brain** (`app/agent/`) | Suggests bundle candidates, discount percentage, confidence score, and one-line reasoning. | Claude 3.5 Haiku / Deterministic rule engine |
| **Safety Engine** (`app/guardrails/`) | Enforces auto-approval ceilings, validates product IDs, verifies positive quantities, clamps discounts. | Pure Python (Zero LLM involvement) |
| **Spine Orchestrator** (`app/orchestrator/`) | Validates idempotency keys, coordinates agent proposals, routes to gateway or human queue, persists audit records. | FastAPI / Python async handlers |
| **Payment Gateway** (`app/razorpay_client/`) | Interacts with Razorpay test-mode API (`/v1/orders`), implements exponential backoff retry. | Razorpay Python SDK (`razorpay`) |
| **Human Review** (`app/approvals/`) | Holds out-of-bounds orders until authorized or rejected by a merchant operator. | File-backed persistent queue |
| **Audit Ledger** (`app/audit/`) | Records immutable, timestamped event logs of every attempt, proposal, guardrail outcome, and payment result. | Append-only JSON ledger (`data/audit_log.json`) |

---

## Safety Guardrails & Thresholds

The system enforces deterministic safety boundaries defined in `app/guardrails/checks.py`:

| Parameter | Auto-Approval Ceiling | Action on Breach |
|---|---|---|
| **Upsell Discount** | `≤ 15%` | Clamped by agent parser; values `> 15%` routed to Human Review |
| **Per-Transaction Spend** | `≤ ₹5,000` (500,000 paise) | Enqueued to `approvals/queue.py` (`pending_human_approval`) |
| **Cumulative Daily Spend** | `≤ ₹20,000` (2,000,000 paise) | Enqueued to `approvals/queue.py` (`pending_human_approval`) |
| **Agent Confidence Score** | `≥ 0.75` (Range: `0.0 - 1.0`) | Enqueued to `approvals/queue.py` (`pending_human_approval`) |
| **Catalog Integrity** | Must exist in `pairs_with` | Rejection of hallucinated product IDs prior to spend |
| **Input Validation** | Quantity must be positive integer | Rejected immediately (`status: "failed"`) before execution |

### Failure Recovery & Resilience
- **Idempotency Protection:** Clients provide an `idempotency_key` with each purchase. Repeated submissions return the cached transaction outcome, guaranteeing that retries over unreliable networks never cause duplicate charges.
- **Fail-to-Human Payment Recovery:** If Razorpay test API calls fail after retry limits (`MAX_RETRIES=2` with exponential backoff), the orchestrator guarantees that **no charge was created**, logs the error, and diverts the order into the merchant review queue.
- **Graceful Brain Degradation:** If Anthropic API credentials are omitted or the model call fails/times out, the system automatically falls back to the deterministic offline decision engine without interrupting the checkout pipeline.

---

## Directory Structure

```
Razorpay-agent-commerce/
├── README.md               # Root submission documentation (this file)
├── CHANGELOG.md            # Version iteration history (v0.1 -> v1.0)
├── .gitignore              # Git ignore rules (venv, .env, __pycache__, data)
├── prompts/                # Prompt engineering evolution artifacts
│   ├── v1/                 # v1: Unbounded conversational prompt
│   ├── v2/                 # v2: Candidate-bounded prompt
│   ├── v3/                 # v3: JSON schema & confidence scoring
│   └── final/              # Production prompt currently running in app/agent/
├── code/                   # Production application source code
│   ├── app/                # Core FastAPI service
│   │   ├── agent/          # Upsell proposal brain (LLM + offline fallback)
│   │   ├── approvals/      # Human review queue & API endpoints
│   │   ├── audit/          # Append-only audit logger & endpoints
│   │   ├── catalog/        # In-memory catalog & schema.org JSON-LD feed
│   │   ├── dashboard/      # Web UI control room & static assets
│   │   ├── guardrails/     # Deterministic financial caps & validators
│   │   ├── orchestrator/   # Checkout pipeline & idempotency controller
│   │   ├── razorpay_client/# Gateway integration & retry logic
│   │   ├── stats/          # Real-time metrics & telemetry
│   │   ├── config.py       # Configuration & environment resolution
│   │   └── main.py         # Application entry point
│   ├── demo/               # Autonomous buyer agent demonstration
│   ├── mcp_server/         # Model Context Protocol server tools
│   ├── tests/              # Pytest test suite
│   ├── requirements.txt    # Python dependencies
│   ├── .env.example        # Environment variable template
│   ├── run.sh              # Unix launch script
│   └── SPEC.md             # Engineering design specification
└── test-data/              # Realistic verification payloads
    ├── sample_catalog_feed.json           # Validated schema.org JSON-LD feed
    ├── valid_checkout_input_output.json   # Happy path with auto-approved upsell
    ├── over_limit_approval_scenario.json  # Over-cap flow routed to human review
    └── payment_failure_recovery.json      # Payment drop, retry & human recovery
```

---

## Setup & Run Instructions

### Prerequisites
- Python 3.10 or higher
- Git

### 1. Navigate to Source Directory
All execution commands must be executed from inside the `code/` folder:
```bash
cd code
```

### 2. Create and Activate Virtual Environment
```bash
# macOS/Linux:
python3 -m venv venv
source venv/bin/activate

# Windows (PowerShell):
python -m venv venv
.\venv\Scripts\Activate.ps1

# Windows (Command Prompt):
python -m venv venv
.\venv\Scripts\activate.bat
```

### 3. Install Dependencies
```bash
pip install -r requirements.txt
```

### 4. Configure Environment Variables (Optional)
The project runs **out of the box with zero external configuration**, automatically creating clearly-labelled mock Razorpay orders and using the deterministic offline brain.

To connect live Razorpay test credentials or Anthropic Claude API:
```bash
cp .env.example .env
```
Edit `.env`:
```ini
# Razorpay TEST Keys (from Razorpay Dashboard -> Settings -> API Keys)
RAZORPAY_KEY_ID=rzp_test_your_test_key_id
RAZORPAY_KEY_SECRET=your_test_key_secret

# LLM Brain: 'auto' | 'anthropic' | 'offline'
LLM_PROVIDER=auto
ANTHROPIC_API_KEY=your_anthropic_api_key
LLM_MODEL=claude-haiku-4-5-20251001

# Resilience Knobs
MAX_RETRIES=2
RETRY_BASE_DELAY_SEC=0.5
```

### 5. Launch the Server
```bash
uvicorn app.main:app --reload
```
The server will bind to `http://127.0.0.1:8000`.

---

## Interactive Endpoints & Surfaces

Once running, access the following surfaces:

- **Merchant Dashboard Control Room:** [`http://127.0.0.1:8000/dashboard`](http://127.0.0.1:8000/dashboard)
  - Live budget consumption gauge (daily spend vs ₹20,000 cap).
  - Storefront catalog viewer.
  - Human review queue with one-click **Approve** and **Reject** buttons.
  - Interactive scenario runners (test normal purchases, over-limit transactions, or trigger simulated payment drops).
  - Live activity ledger streaming audit records.
- **Interactive OpenAPI Documentation:** [`http://127.0.0.1:8000/docs`](http://127.0.0.1:8000/docs)
- **Machine-Readable Agent Feed:** [`http://127.0.0.1:8000/catalog/agent-feed`](http://127.0.0.1:8000/catalog/agent-feed)
  - schema.org JSON-LD structured product metadata for autonomous web agents.

### Running the Autonomous Buyer Agent Demo
To witness an autonomous agent discover products from the feed and transact without human intervention:
```bash
# From within the code/ directory:
python -m demo.buyer_agent
```

### Running the Model Context Protocol (MCP) Server
To expose the agent-readable catalog and checkout tools to MCP-enabled clients (e.g., Claude Desktop, cursor, or Antigravity):
```bash
# From within the code/ directory:
python -m mcp_server.server
```

---

## Verification & Automated Tests

A comprehensive Pytest suite validates guardrails, idempotency, retry mechanisms, and human approval queues.

Run the tests from inside `code/`:
```bash
pytest -v
```

### Test Coverage Highlights
- `test_guardrails.py`: Validates discount ceiling enforcement (≤15%), per-transaction limits (₹5,000), cumulative daily limits (₹20,000), confidence bounds (≥0.75), and malformed payload filtering.
- `test_orchestrator.py`:
  - `test_idempotent_replay`: Verifies that sending the exact same idempotency key never charges twice and returns the original order.
  - `test_over_limit_queues_for_human`: Confirms large baskets are held in the approval queue rather than auto-executed.
  - `test_payment_failure_retry_and_route`: Simulates payment drops, verifies exponential backoff retry, ensures zero funds deducted, and checks routing to human review.
  - `test_brain_fallback`: Confirms seamless failover to deterministic brain when LLM provider is disabled or fails.

---

## API Reference

| Method | Endpoint | Description |
|---|---|---|
| `GET` | `/catalog/products` | Lists merchant catalog items, supporting category filters |
| `GET` | `/catalog/products/{id}` | Fetches individual product details and inventory |
| `GET` | `/catalog/products/{id}/availability` | Real-time stock verification for shopping agents |
| `GET` | `/catalog/agent-feed` | Machine-native schema.org JSON-LD catalog feed |
| `POST` | `/checkout` | Bounded checkout pipeline enforcing idempotency & guardrails |
| `GET` | `/approvals/` | Lists pending, approved, and rejected human review items |
| `POST` | `/approvals/{id}/approve` | Merchant executes a previously held transaction |
| `POST` | `/approvals/{id}/reject` | Merchant rejects a flagged transaction |
| `GET` | `/audit/logs` | Returns append-only audit trail records |
| `GET` | `/stats` | Telemetry endpoint (daily spend, approval counts, mode) |
| `POST` | `/demo/arm-failure` | Demo control: arms mock gateway to simulate transient drops |
| `POST` | `/demo/reset` | Resets local test state (daily totals, audit logs, queues) |

---

## Judging Criteria Alignment

| Buildathon Criterion | Implementation Evidence |
|---|---|
| **Problem Taste** | Solves two real problems at once: increasing merchant AOV via contextual upsells and opening merchant inventories to autonomous AI buyers via JSON-LD & MCP. |
| **Build Quality & Architecture** | Modular separation of concerns (`agent`, `guardrails`, `orchestrator`, `approvals`, `audit`, `razorpay_client`). Zero leaky abstractions. |
| **AI Judgment vs Determinism** | The LLM solely *proposes*; pure deterministic Python code *governs and decides*. Hallucinated items and unauthorized discounts are physically blocked. |
| **Failure Recovery & Resilience** | Guaranteed idempotency against network replays, exponential retry backoff on Razorpay API, fail-to-human recovery without double charging. |
| **Safety & Merchant Control** | Hard spending caps, daily cumulative budget tracking, minimum confidence gating, and a live human approval queue. |
| **Transparency & Audit Trail** | Every proposal, model score, guardrail evaluation, and gateway interaction is logged immutably in an append-only ledger. |
