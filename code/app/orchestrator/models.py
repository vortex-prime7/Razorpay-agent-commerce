from pydantic import BaseModel, Field


class CheckoutRequest(BaseModel):
    base_product_id: str
    quantity: int = 1
    # Client-supplied key that makes retries safe: the same key never
    # produces a second charge. An autonomous buyer should generate one
    # per logical purchase and reuse it if it has to retry.
    idempotency_key: str = Field(..., description="Unique per logical purchase; reused on retry")


class CheckoutResult(BaseModel):
    status: str                 # "completed" | "pending_human_approval" | "failed" | "replayed"
    message: str
    order_id: str | None = None
    amount_paise: int | None = None
    upsell_offered: bool = False
    addon_product_id: str | None = None
    discount_percent: int = 0
    agent_confidence: float | None = None
    agent_provider: str | None = None
    audit_id: str | None = None
    approval_id: str | None = None
