#!/usr/bin/env bash
# Starts the ClaimShield API on 127.0.0.1:8000 with a review-only SQLite DB.
cd /workspace/ACENTRA_ClaimShield_Nexus/backend
export CLAIMSHIELD_DATABASE_URL="sqlite+pysqlite:////workspace/claimshield-review/claimshield_review.db"
export CLAIMSHIELD_JWT_SIGNING_KEY="review-only-signing-key-0123456789"
export CLAIMSHIELD_COOKIE_SECURE=false
export CLAIMSHIELD_DEMO_MODE=true
export CLAIMSHIELD_DATA_PROFILE=tiny
nohup uv run --no-sync uvicorn claimshield.api.main:app --app-dir src --host 127.0.0.1 --port 8000 \
  > /workspace/claimshield-review/logs/api.log 2>&1 &
echo $! > /workspace/claimshield-review/logs/api.pid
