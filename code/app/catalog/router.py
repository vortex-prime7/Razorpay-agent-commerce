"""
The agent-readable catalog (REST spine). Any AI shopping agent can hit these
and get structured, unambiguous product data — no HTML scraping. The
/agent-feed endpoint returns schema.org JSON-LD, the machine-native format.
"""
from fastapi import APIRouter, HTTPException

from app.catalog.data import PRODUCTS, PRODUCT_INDEX
from app.catalog.models import Product

router = APIRouter()


@router.get("/products", response_model=list[Product])
def list_products(category: str | None = None):
    """List all products, optionally filtered by category."""
    if category:
        return [p for p in PRODUCTS if p.category == category]
    return PRODUCTS


@router.get("/products/{product_id}", response_model=Product)
def get_product(product_id: str):
    product = PRODUCT_INDEX.get(product_id)
    if not product:
        raise HTTPException(status_code=404, detail=f"Product '{product_id}' not found")
    return product


@router.get("/products/{product_id}/availability")
def check_availability(product_id: str, quantity: int = 1):
    """An agent should call this before attempting checkout."""
    product = PRODUCT_INDEX.get(product_id)
    if not product:
        raise HTTPException(status_code=404, detail=f"Product '{product_id}' not found")
    return {
        "product_id": product_id,
        "requested": quantity,
        "in_stock": product.stock >= quantity,
        "available_stock": product.stock,
    }


@router.get("/agent-feed")
def agent_feed():
    """
    schema.org JSON-LD feed — the machine-native catalog contract for
    autonomous buyers. This is the 'AI-to-AI shopping' surface.
    """
    return {
        "@context": "https://schema.org",
        "@type": "ItemList",
        "itemListElement": [p.to_json_ld() for p in PRODUCTS],
    }
