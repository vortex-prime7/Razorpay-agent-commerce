"""
Single source of truth for configuration. Everything tunable lives here
so a judge (or you, in the demo) can see and change the knobs in one place.

Nothing in this file is secret — real secrets come from the environment
(.env), never from code.
"""
import os
from pathlib import Path

from dotenv import load_dotenv

load_dotenv()

# --- Where runtime data (audit log, approval queue, daily totals) is written.
# File-based on purpose: no database to stand up, survives restarts, easy to
# inspect and easy to reset for a clean demo.
DATA_DIR = Path(os.environ.get("DATA_DIR", "data"))
DATA_DIR.mkdir(parents=True, exist_ok=True)

AUDIT_LOG_PATH = DATA_DIR / "audit_log.jsonl"
APPROVAL_QUEUE_PATH = DATA_DIR / "approval_queue.json"
DAILY_TOTALS_PATH = DATA_DIR / "daily_totals.json"
IDEMPOTENCY_PATH = DATA_DIR / "idempotency.json"

# --- Razorpay test-mode credentials (from .env). Absent = client runs in a
# clearly-labelled "unconfigured" state so the app still boots for a dry run.
RAZORPAY_KEY_ID = os.environ.get("RAZORPAY_KEY_ID", "")
RAZORPAY_KEY_SECRET = os.environ.get("RAZORPAY_KEY_SECRET", "")

# --- LLM provider selection. The agent is provider-swappable. If no key is
# present we fall back to "offline" (deterministic rules) automatically, which
# also keeps a live demo alive if the network or key fails.
#   LLM_PROVIDER = "anthropic" | "offline"
LLM_PROVIDER = os.environ.get("LLM_PROVIDER", "auto")
ANTHROPIC_API_KEY = os.environ.get("ANTHROPIC_API_KEY", "")
LLM_MODEL = os.environ.get("LLM_MODEL", "claude-haiku-4-5-20251001")


def resolve_provider() -> str:
    """Decide which agent brain to use, given what's configured."""
    if LLM_PROVIDER == "offline":
        return "offline"
    if LLM_PROVIDER == "anthropic":
        return "anthropic" if ANTHROPIC_API_KEY else "offline"
    # "auto": use Anthropic if a key exists, otherwise offline.
    return "anthropic" if ANTHROPIC_API_KEY else "offline"


# --- Failure-handling knobs for the Razorpay call path.
MAX_RETRIES = int(os.environ.get("MAX_RETRIES", "2"))       # retries after first attempt
RETRY_BASE_DELAY_SEC = float(os.environ.get("RETRY_BASE_DELAY_SEC", "0.5"))
