# ClaimShield Nexus

Post-adjudication SIU platform for Medicaid-like FWA: synthetic extract, hash-chained audit, cookie JWT + RBAC auth, rules + peer anomaly + graph cases, capacity knapsack queue.

This repository contains the backend, auth, product docs, and the SIU frontend (queue, worklist, investigation workspace).

## Docs

| File | What it is |
| --- | --- |
| [01_PS3_research_brief.md](01_PS3_research_brief.md) | Problem statement research brief |
| [CLAIMSHIELD_NEXUS_PLAN.md](CLAIMSHIELD_NEXUS_PLAN.md) | Combined product and engineering plan |
| [CLAIMSHIELD_PLAN_DRAFT.md](CLAIMSHIELD_PLAN_DRAFT.md) | Plan draft |
| [IDEATION_AND_IMPROVEMENTS.md](IDEATION_AND_IMPROVEMENTS.md) | Ideation notes |
| [data/reference/PAPERS.md](data/reference/PAPERS.md) | Research map for detectors and schemes |
| [backend/README.md](backend/README.md) | Backend runbook |
| [docs/MODEL_CARD.md](docs/MODEL_CARD.md) | Risk models: labels, backtest, calibration, limits |

## Backend

```
cd backend
uv sync --extra dev
copy .env.example .env
uv run pytest
uv run uvicorn claimshield.api.main:app --reload --app-dir src --host 127.0.0.1 --port 8000
```

Generate the tiny extract (CSV + data card; ground truth kept separate):

```
uv run python -m claimshield generate --profile tiny --seed 7
```

Train the risk models (P(confirm) and the 30/60/90-day hazard) on 24 seeded `panel` worlds and write `data/models/risk_model.json` (about 1–2 minutes on CPU; `make train` does the same):

```
uv run python -m claimshield train --profile panel --seed 7
```

The pipeline loads that artifact on every run. Without it, scores fall back to a labelled "uncalibrated heuristic". Artifact summary and backtest metrics: `GET /api/v1/models/risk` (roles with `model:read`). Method, numbers and limits: [docs/MODEL_CARD.md](docs/MODEL_CARD.md).

Docker: `docker compose up` from the repo root (Postgres + API).

## Frontend

```
cd frontend
npm install
npm run dev
```

Vite proxies `/api` to `http://127.0.0.1:8000`. Landing `/` is a scroll-driven Three.js story. Product routes: `/login`, `/manager/queue`, `/investigator/cases`, `/investigator/workspace/:caseId`, `/wiki/proposals`, `/audit`.

## Auth

Auth lives in `backend/src/claimshield/auth/` (Argon2id passwords, JWT cookies, RBAC, login rate limits). HTTP surface: `POST /api/v1/auth/login`, refresh, logout, `GET /api/v1/auth/me`. Cookies: `cs_access`, `cs_refresh`, `cs_csrf`.

Demo users (demo mode):

| Email | Password | Role |
| --- | --- | --- |
| investigator@demo.claimshield | demo-investigator | investigator |
| investigator2@demo.claimshield | demo-investigator2 | investigator |
| manager@demo.claimshield | demo-manager | manager |
| analyst@demo.claimshield | demo-analyst | analyst |
| auditor@demo.claimshield | demo-auditor | auditor |
| admin@demo.claimshield | demo-admin | admin |

Manager loads data: `POST /api/v1/batches` `{"profile":"tiny","seed":7}`. Queue: `GET /api/v1/runs/{run_id}/queue`.

S3 ingest (optional, not required for local demo): Lambda `claimshield-s3-processor` calls `POST /api/v1/aws/ingest` with `X-ClaimShield-Internal-Token`. See [docs/AWS_INGEST.md](docs/AWS_INGEST.md). Local synthetic load does not need AWS.

Investigation workspace: `/investigator/workspace/:caseId`. APIs: `GET /api/v1/cases/{id}` plus `/brief`, `/claims`, `/timeline`, `/network`, `/evidence/{item_id}`; `POST /api/v1/cases/{id}/decisions`.

## Dataset notes

Planted schemes S01–S21, rings G1–G3, camouflage C1, hard negatives HN1–HN2. S06 ambulance providers are excluded from risk-model training and scored as an unseen scheme in the backtest (still visible to rules; see [docs/MODEL_CARD.md](docs/MODEL_CARD.md)). No CPT. Synthetic NPIs pass Luhn. Ground truth is labels only and is not a feature table.
