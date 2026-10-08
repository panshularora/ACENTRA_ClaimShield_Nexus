# ClaimShield Nexus backend

SIU case platform: synthetic Medicaid-like extract, hash-chained audit, cookie JWT auth, rules + peer anomaly + graph cases, capacity knapsack queue.

## Quick start

```
uv sync --frozen --extra dev
cp .env.example .env
uv run pytest
uv run uvicorn claimshield.api.main:app --reload --app-dir src --host 127.0.0.1 --port 8000
```

Write the tiny extract (CSV + data card, ground truth kept separate):

```
uv run python -m claimshield generate --profile tiny --seed 7
```

Train the risk models (P(confirm) and the 30/60/90-day hazard) on 24 seeded `panel` worlds and write `../data/models/risk_model.json` (about 1–2 minutes on CPU; `make train` does the same):

```
uv run python -m claimshield train --profile panel --seed 7
```

The pipeline loads that artifact on every run. Without it, scores fall back to a labelled "uncalibrated heuristic". Artifact summary and backtest metrics: `GET /api/v1/models/risk` (roles with `model:read`). Method, numbers and limits: [../docs/MODEL_CARD.md](../docs/MODEL_CARD.md).

## Demo users (demo mode)

| Email | Password | Role |
| --- | --- | --- |
| investigator@demo.claimshield | demo-investigator | investigator |
| investigator2@demo.claimshield | demo-investigator2 | investigator |
| manager@demo.claimshield | demo-manager | manager |
| analyst@demo.claimshield | demo-analyst | analyst |
| auditor@demo.claimshield | demo-auditor | auditor |
| admin@demo.claimshield | demo-admin | admin |

Login: `POST /api/v1/auth/login`. Cookies: `cs_access`, `cs_refresh`, `cs_csrf`.
Manager loads data: `POST /api/v1/batches` `{"profile":"tiny","seed":7}`.
AWS machine ingest: `POST /api/v1/aws/ingest` with `X-ClaimShield-Internal-Token` (see `../docs/AWS_INGEST.md`). Leave `CLAIMSHIELD_INTERNAL_TOKEN` empty for local-only use. Lambda `claimshield-s3-processor` in `ap-south-1` must use the same token. `GET /api/v1/aws/status` shows bucket and prefixes and never returns the secret.
Queue: `GET /api/v1/runs/{run_id}/queue`.
Workspace: `GET /api/v1/cases/{id}` plus `/brief`, `/claims`, `/timeline`, `/network`, `/evidence/{item_id}`.
Decide: `POST /api/v1/cases/{id}/decisions` `{action, ladder_step, reason, evidence_refs}` (escalate | monitor | dismiss | needs_evidence; reason 20–4000 chars). Options and the allowed steps per action: `GET /api/v1/cases/{id}/decision-options`. Escalations wait in `pending_approval` until a different manager calls `POST /api/v1/decisions/{id}:approve` or `:reject`. Never an automatic fraud label.
Session probe: `GET /api/v1/auth/session` (always 200). Cookie-authenticated writes need `X-CSRF-Token` equal to the `cs_csrf` cookie.

Checks: `make check` (ruff lint, ruff format check, mypy strict, pytest).

## Dataset

Planted schemes S01–S21, rings G1–G3, camouflage C1, hard negatives HN1–HN2.
S06 ambulance providers are excluded from risk-model training and scored as an unseen scheme in the backtest (still visible to rules; see `../docs/MODEL_CARD.md`).
No CPT. Synthetic NPIs pass Luhn. Ground truth is not a feature table.

Research map: `../data/reference/PAPERS.md`.
