"""
Entry point. Run with:
    uvicorn app.main:app --reload

Key URLs:
    /              health check
    /dashboard     operations control room (audit trail + approval queue + demo buttons)
    /docs          interactive, agent-readable API docs
    /catalog/agent-feed   schema.org JSON-LD product feed for autonomous buyers
"""
from fastapi import FastAPI

from app.config import resolve_provider
from app.catalog.router import router as catalog_router
from app.orchestrator.router import router as checkout_router
from app.approvals.router import router as approvals_router
from app.audit.router import router as audit_router
from app.dashboard.router import router as dashboard_router
from app.stats.router import router as stats_router

app = FastAPI(
    title="Agent Commerce Layer",
    description="Agent-readable catalog + bounded upsell agent on Razorpay test-mode APIs.",
    version="1.0.0",
)

app.include_router(catalog_router, prefix="/catalog", tags=["catalog"])
app.include_router(checkout_router, tags=["checkout"])
app.include_router(approvals_router, prefix="/approvals", tags=["approvals"])
app.include_router(audit_router, prefix="/audit", tags=["audit"])
app.include_router(dashboard_router, prefix="/dashboard", tags=["dashboard"])
app.include_router(stats_router, tags=["telemetry"])


@app.get("/", tags=["health"])
def health_check():
    return {
        "status": "ok",
        "service": "agent-commerce-layer",
        "agent_brain": resolve_provider(),  # "anthropic" or "offline"
        "dashboard": "/dashboard",
        "docs": "/docs",
    }
