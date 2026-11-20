"""
MCP server — the headline "AI-to-AI shopping" surface.

This exposes the SAME catalog and the SAME bounded checkout flow as the REST
API, but as Model Context Protocol *tools*. Any MCP-speaking agent (Claude
Desktop, an autonomous shopping agent, etc.) can discover and call these
tools directly — that's what "agent-native commerce" means in practice.

There is one source of truth: these tools call the exact same orchestrator
as the REST path, so the guardrails, audit trail, and failure handling all
still apply. The protocol changes; the safety does not.

Run:  pip install mcp   then   python -m mcp_server.server
(Register it in your MCP client's config to use it from an agent.)
"""
from mcp.server.fastmcp import FastMCP

from app.catalog.data import PRODUCTS, PRODUCT_INDEX
from app.orchestrator.checkout import checkout

mcp = FastMCP("agent-commerce")


@mcp.tool()
def list_products(category: str | None = None) -> list[dict]:
    """List catalog products, optionally filtered by category."""
    items = PRODUCTS if not category else [p for p in PRODUCTS if p.category == category]
    return [p.model_dump() for p in items]


@mcp.tool()
def get_product(product_id: str) -> dict:
    """Get one product by id. Returns an error dict if not found."""
    p = PRODUCT_INDEX.get(product_id)
    return p.model_dump() if p else {"error": f"Product '{product_id}' not found"}


@mcp.tool()
def check_availability(product_id: str, quantity: int = 1) -> dict:
    """Check whether `quantity` of a product is in stock before buying."""
    p = PRODUCT_INDEX.get(product_id)
    if not p:
        return {"error": f"Product '{product_id}' not found"}
    return {"product_id": product_id, "in_stock": p.stock >= quantity, "available_stock": p.stock}


@mcp.tool()
def buy(base_product_id: str, quantity: int, idempotency_key: str) -> dict:
    """
    Attempt a purchase. Goes through the full bounded pipeline: the upsell
    agent may add an offer, guardrails decide auto vs. human approval, and
    everything is written to the audit trail. Reuse the same idempotency_key
    on retry so a repeat never double-charges.
    """
    return checkout(base_product_id, quantity, idempotency_key).model_dump()


if __name__ == "__main__":
    mcp.run()
