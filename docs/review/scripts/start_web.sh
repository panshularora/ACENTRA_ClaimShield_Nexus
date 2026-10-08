#!/usr/bin/env bash
# Starts the Vite dev server on 127.0.0.1:5173 (proxies /api to :8000).
cd /workspace/ACENTRA_ClaimShield_Nexus/frontend
nohup npm run dev -- --host 127.0.0.1 --port 5173 --strictPort \
  > /workspace/claimshield-review/logs/web.log 2>&1 &
echo $! > /workspace/claimshield-review/logs/web.pid
