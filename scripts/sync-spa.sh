#!/usr/bin/env bash
set -euo pipefail
root="$(cd "$(dirname "$0")/.." && pwd)"
api_base="${VITE_API_BASE:-https://claimshield-nexus-api.onrender.com}"
cd "$root/frontend"
VITE_API_BASE="$api_base" npm run build
rm -rf "$root/backend/spa"
mkdir -p "$root/backend/spa"
cp -R dist/. "$root/backend/spa/"
echo "synced $root/backend/spa for FastAPI hosting"
