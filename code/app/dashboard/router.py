"""Serves the single-file operations dashboard (audit trail + approval queue).
Served by FastAPI itself so the whole demo runs with one command — no separate
frontend process to start."""
from pathlib import Path

from fastapi import APIRouter
from fastapi.responses import HTMLResponse

router = APIRouter()

_HTML = (Path(__file__).parent / "static" / "dashboard.html").read_text(encoding="utf-8")


@router.get("/", response_class=HTMLResponse)
def dashboard():
    return _HTML
