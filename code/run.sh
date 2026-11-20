#!/usr/bin/env bash
# One-command run. Creates a venv on first use, installs deps, starts the server.
set -e
if [ ! -d venv ]; then
  python -m venv venv
fi
source venv/bin/activate
pip install -q -r requirements.txt
[ -f .env ] || cp .env.example .env
echo "Server: http://127.0.0.1:8000  |  Dashboard: http://127.0.0.1:8000/dashboard  |  Docs: /docs"
uvicorn app.main:app --reload
