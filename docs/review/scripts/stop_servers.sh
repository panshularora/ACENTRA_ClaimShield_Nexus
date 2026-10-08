#!/usr/bin/env bash
# Stops the review API (uvicorn on :8000) and Vite dev server (:5173).
pkill -f "uvicorn claimshield.api.main:app" || true
pkill -f "vite --host 127.0.0.1 --port 5173" || true
pkill -f "node .*vite" || true
