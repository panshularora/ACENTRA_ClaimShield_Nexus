# ClaimShield Nexus

Post-adjudication SIU platform for Medicaid-like FWA: synthetic extract, hash-chained audit, cookie JWT + RBAC auth, rules + peer anomaly + graph cases, capacity knapsack queue.

This repository contains the backend, auth, product docs, and the SIU frontend (queue, worklist, investigation workspace).

## Docs

| File | What it is |
| --- | --- |
| [01_PS3_research_brief.md](01_PS3_research_brief.md) | Problem statement research brief |
| [CLAIMSHIELD_NEXUS_PLAN.md](CLAIMSHIELD_NEXUS_PLAN.md) | Combined product and engineering plan |
| [IDEATION_AND_IMPROVEMENTS.md](IDEATION_AND_IMPROVEMENTS.md) | Ideation notes |
| [data/reference/PAPERS.md](data/reference/PAPERS.md) | Research map for detectors and schemes |
| [backend/README.md](backend/README.md) | Backend runbook |
| [docs/MODEL_CARD.md](docs/MODEL_CARD.md) | Risk models: labels, backtest, calibration, limits |

## Backend

```
cd backend
uv sync --frozen --extra dev
cp .env.example .env
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

Quality gates (the same commands run in CI):

```
uv run ruff check src tests
uv run ruff format --check src tests
uv run mypy
```

First run: sign in as the manager and click "Load tiny run" (or `POST /api/v1/batches` `{"profile":"tiny","seed":7}`). The queue and worklists stay empty until a batch is loaded.

Docker: `docker compose up` from the repo root (Postgres + API). The image installs from `uv.lock` with `uv sync --frozen`. The compose file runs in demo mode; outside demo mode the API refuses to start unless `CLAIMSHIELD_JWT_SIGNING_KEY` is a non-placeholder key of at least 32 bytes. The compose setup has not been exercised in CI.

## Frontend

```
cd frontend
npm install
npm run dev
```

Vite proxies `/api` to `http://127.0.0.1:8000`. Landing `/` is a scroll-driven Three.js story. Product routes: `/login`, `/manager/queue`, `/investigator/cases`, `/investigator/workspace/:caseId`, `/wiki/proposals`, `/audit`.

## Auth

Auth lives in `backend/src/claimshield/auth/` (Argon2id passwords, JWT cookies, RBAC, login rate limits). HTTP surface: `POST /api/v1/auth/login`, refresh, logout, `GET /api/v1/auth/me` (401 when signed out), `GET /api/v1/auth/session` (always 200, `authenticated` flag). Cookies: `cs_access`, `cs_refresh`, `cs_csrf`. Every cookie-authenticated write must send `X-CSRF-Token` equal to the `cs_csrf` cookie. Failed logins and refresh-token reuse are written to the audit chain.

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

Investigation workspace: `/investigator/workspace/:caseId`. APIs: `GET /api/v1/cases/{id}` plus `/brief`, `/claims`, `/timeline`, `/network`, `/decision-options`, `/evidence/{item_id}`; `/network/nodes/{node_id}`; `GET /api/v1/entities/{id}/summary?case_id=`. The network contract, with a real seeded example, is in [docs/NETWORK_API.md](docs/NETWORK_API.md).

Decision workflow: the assigned investigator posts `POST /api/v1/cases/{id}/decisions` `{action, ladder_step, reason, evidence_refs}` (reason 20–4000 characters). `monitor`, `needs_evidence` and `dismiss` apply immediately. `escalate` goes to `pending_approval`, and a different manager approves (`POST /api/v1/decisions/{id}:approve`) or rejects it (`:reject`, note of at least 20 characters). A manager can reopen a closed case (`POST /api/v1/cases/{id}/reopen`). Every step is audited, and a decision is never an automatic fraud label.

## Limitations

- All data is synthetic. Detector thresholds and planted schemes have not been validated against real Medicaid claims.
- Exclusion (LEIE) matching runs against a synthetic exclusion file; it requires NPI plus name, or name, date of birth and address, inside the exclusion window.
- The default database is SQLite. Postgres via Docker compose is not covered by tests.

## Dataset notes

Planted schemes S01–S21, rings G1–G3, camouflage C1, hard negatives HN1–HN2. S06 ambulance providers are excluded from risk-model training and scored as an unseen scheme in the backtest (still visible to rules; see [docs/MODEL_CARD.md](docs/MODEL_CARD.md)). No CPT. Synthetic NPIs pass Luhn. Ground truth is labels only and is not a feature table.
