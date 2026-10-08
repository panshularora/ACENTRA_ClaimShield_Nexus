# ClaimShield Nexus backend

SIU case platform: synthetic Medicaid-like extract, hash-chained audit, cookie JWT auth, rules + peer anomaly + graph cases, capacity knapsack queue.

## Quick start

```
uv sync --extra dev
copy .env.example .env
uv run pytest
uv run uvicorn claimshield.api.main:app --reload --app-dir src --host 127.0.0.1 --port 8000
```

Write the tiny extract (CSV + data card, ground truth kept separate):

```
uv run python -m claimshield generate --profile tiny --seed 7
```

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
Queue: `GET /api/v1/runs/{run_id}/queue`.
Workspace: `GET /api/v1/cases/{id}` plus `/brief`, `/claims`, `/timeline`, `/network`, `/evidence/{item_id}`.
Decide: `POST /api/v1/cases/{id}/decisions` `{action, reason}` (escalate | monitor | dismiss | needs_evidence; reason ≥ 20 chars). Never an automatic fraud label.

## Dataset

Planted schemes S01–S21, rings G1–G3, camouflage C1, hard negatives HN1–HN2.
S06 ambulance is held out of model training (still visible to rules).
No CPT. Synthetic NPIs pass Luhn. Ground truth is not a feature table.

Research map: `../data/reference/PAPERS.md`.
