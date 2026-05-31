#!/bin/bash
export PYTHONPATH=/home/runner/workspace/.pythonlibs/lib/python3.12/site-packages:$PYTHONPATH
/home/runner/workspace/.pythonlibs/bin/python3.12 -m uvicorn api.main:app --host 0.0.0.0 --port 5000
