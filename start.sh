#!/bin/bash
# Use system Python (works in both Replit dev and deployed environments)
PYTHON=$(command -v python3 || command -v python)
export PYTHONPATH="${PYTHONPATH}:/home/runner/workspace/.pythonlibs/lib/python3.12/site-packages"
exec "$PYTHON" -m uvicorn api.main:app --host 0.0.0.0 --port 5000
