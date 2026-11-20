"""Test setup: isolate runtime data to a temp dir and force the offline brain,
BEFORE any app module (which reads config at import) is imported."""
import os
import tempfile

os.environ["DATA_DIR"] = tempfile.mkdtemp(prefix="rzp_test_")
os.environ["LLM_PROVIDER"] = "offline"
os.environ.pop("RAZORPAY_KEY_ID", None)       # no keys -> mock orders in tests
os.environ.pop("RAZORPAY_KEY_SECRET", None)

import pytest
from app.config import (
    AUDIT_LOG_PATH, APPROVAL_QUEUE_PATH, DAILY_TOTALS_PATH, IDEMPOTENCY_PATH,
)


@pytest.fixture(autouse=True)
def clean_data():
    """Wipe all runtime files before each test for a clean slate."""
    for p in (AUDIT_LOG_PATH, APPROVAL_QUEUE_PATH, DAILY_TOTALS_PATH, IDEMPOTENCY_PATH):
        if p.exists():
            p.unlink()
    yield
