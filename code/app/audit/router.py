"""HTTP surface for the audit trail. This endpoint is what the dashboard polls."""
from fastapi import APIRouter

from app.audit.logger import read_log

router = APIRouter()


@router.get("/logs")
def get_logs():
    """Full audit trail, newest first."""
    return list(reversed(read_log()))
