# ClaimShield Nexus — build log, demo, and judging map

Acentra Health code-a-thon, Problem 3. Product: post-adjudication SIU workbench for Medicaid-like claims.

Live demo:

- App: https://claimshield-nexus.vercel.app
- API: https://claimshield-nexus-api.vercel.app
- Repo: https://github.com/panshularora/ACENTRA_ClaimShield_Nexus
- Branch with this slice: `feature/frontend-backend-wiring`

Demo logins (demo mode only):

| Role | Email | Password |
| --- | --- | --- |
| Manager | manager@demo.claimshield | demo-manager |
| Investigator | investigator@demo.claimshield | demo-investigator |

## What the product does

ClaimShield sits after a claims engine such as eCAMS. It groups detector hits into **network cases**, ranks them inside **investigator hours**, and gives a human a cited packet. It recommends. It never writes “fraud” as a label. Payment suspension stays a state decision (42 CFR 455.23) and needs a manager.

Headline metric on the manager desk: **N alerts → M cases → K selected today**.

Four detection layers fire on the same extract:

1. Catalog rules (duplicates, after-death DME, EVV gaps, LEIE, PTP/units, BH hours, inpatient overlap).
2. Like-with-like peer anomaly.
3. Calibrated P(confirm) plus 30/60/90-day hazard (`docs/MODEL_CARD.md`).
4. Identity graph (TIN, owner, contact, referral) so a telefraud ring is one case.

Queue rank is a **weighted composite** of scheme severity, financial exposure, member impact, evidence strength, and urgency. Harm-priority cases jump the dollar sort. Displayed percentages cap at 99 — the UI never presents a score as certainty.

## Architecture

```
S3 incoming/*.csv
    → Lambda claimshield-s3-processor (ap-south-1)
    → POST /api/v1/aws/ingest  (X-ClaimShield-Internal-Token)
    → persist_dataset + execute_run
    → SQLite (demo) / Postgres (compose)
    → React SIU desk
```

Local and Vercel demo also load a synthetic **tiny/seed 7** extract through `POST /api/v1/batches`.

Stack:

- FastAPI 0.115, SQLAlchemy 2, Argon2id JWT cookies, hash-chained audit.
- Vite 8, React 19, TanStack Router/Query, Recharts, Cytoscape.js + fcose.
- boto3 for live S3. Lambda is a thin trigger; fraud logic stays in the API.

## What we actually built (chronology)

Work landed on `feature/frontend-backend-wiring` and the Vercel pair above.

1. **Backend spine.** Generator, detectors, case builder, capacity knapsack, template brief, decision → audit → precedent → manager approval.
2. **Auth and RBAC.** Cookie JWT, CSRF, demo users with **stable IDs** so serverless JWT `sub` survives instance hops.
3. **Frontend desk.** Manager queue (horizon, capacity, factor bars, compare strip), investigator worklist, investigation workspace.
4. **Evidence packet.** Findings and the evidence drawer share `EvidenceStory`: plain “what we saw / what we checked”, highlights, optional peer chart, then a folded “Technical — how this was produced”. Provenance has the same split. Rank contribution chart points = score × weight × 100 and sum to combined rank.
5. **History.** Closed SIU cases, earlier-run cases, and extract investigations. Outcomes stay substantiated / education / referred / unsubstantiated. The list is **10 rows per page** with Next / Previous.
6. **AWS ingest.** Bucket `claimshield-nexus-data-2026`, prefixes `incoming/`, `processed/`, `results/`, function `claimshield-s3-processor`, region `ap-south-1`. FastAPI accepts both `CLAIMSHIELD_*` and the unprefixed sheet names (`AWS_REGION`, `S3_BUCKET`, `S3_INPUT_PREFIX`, …). Lambda and API share one internal token. `GET /api/v1/aws/status` shows wiring and recent receipts and **never returns the token**.
7. **Public demo.** Frontend and API on Vercel. Cross-site cookies: public HTTPS Origin → SameSite=None; Secure. CORS allows `*.vercel.app`. Auto-seed tiny/7 when the serverless `/tmp` database is empty.

## Judging metrics

### Technical merit

- Four layers plus graph grouping, with tests (`backend/tests/test_detectors.py`, `test_grouping.py`, `test_network.py`, `test_aws_ingest.py`, `test_lambda_s3.py`).
- Rank math is explicit and testable (`queue/rank.py`, `factorData.ts`).
- Ingest is idempotent (`IngestReceipt` fingerprint). Incomplete drops return `waiting_for_tables`. Same ETags return `already_processed`.
- LEIE match is NPI + name + exclusion date. CMS-style one-sided 90% CI lower bound on peer residuals. NetworkX Leiden `metric="modularity"`.
- Serverless demo constraints handled: stable user IDs, auto-seed, Origin-aware cookies.

### Design, UI, UX

- SIU look: IBM Plex, paper `#efe8d6`, ink `#161c22`, harm brick, dense tables, 4px lane rails.
- Case header keeps **subject · provider · suspicion**. Axes tiles: suspicion, scheme severity, financial exposure, member impact, evidence strength, urgency.
- Evidence is readable first, technical on demand. Charts use `ChartPlot` with an explicit `initialDimension` so Recharts does not collapse in CSS grid.
- History pager: ten rows, Next to continue, filter and search reset the page.

### Presentation / demo (about four minutes)

1. Landing `/` — “a case is a network”, 45-day clock, recommend-only.
2. Manager login → queue. Point at **N alerts → M cases → K desk**. Move horizon/capacity, recompute.
3. Open AWS ingest panel: region, bucket, prefixes, Lambda, token configured.
4. Investigator login → worklist. Open a harm-priority case (McGee-class DME / after-death or the ring).
5. Evidence tab: plain finding → peer chart → technical fold. Rank chart segments add to combined rank.
6. Network tab: 2-hop identity graph. Decision bar: escalate / monitor / dismiss / needs evidence, reason ≥ 20 characters.
7. History: ten rows, click Next. Outcome language only.

### Teamwork and time management

The written plan (M1–M16 plus stretch) is larger than a hackathon. The slice we shipped is the vertical path judges can click: generate or ingest → detect → group → rank inside hours → cited packet → human decision → audit/history. Stretch items that would steal the demo (X12, whole-ring Sigma, displacement watch, sampling CI, referral export, auto rule suggestions) stayed off the critical path. AWS ingest stayed in the repo and is wired, because the drop path is part of the story.

### Usefulness

A Monday-morning SIU desk: hours are the scarce resource, harm jumps the line, evidence is cited, the state still decides. Improper-payment rates stay documentation-heavy figures; they are never presented as a fraud rate.

### Uniqueness

Most FWA dashboards sort dollars or dump alerts. ClaimShield treats **the case as a network**, packs a **capacity knapsack**, and shows **plain + technical evidence** for the same finding. The S3 drop reuses that pipeline instead of putting rules in Lambda.

### Code quality (AI scoring)

- Module comments on ingest, history, evidence, Lambda handler.
- AWS path is kept and tested (`test_aws_ingest.py`, `test_lambda_s3.py`).
- Secrets stay in environment variables. `.env` is gitignored. Status endpoints redact tokens.
- Display cap at 99% is intentional product language, documented in `format.ts`.
- boto3 is a runtime dependency so the API can talk to S3 on Vercel.

## AWS run sheet (implemented)

| Variable | Value |
| --- | --- |
| AWS_REGION | ap-south-1 |
| S3_BUCKET | claimshield-nexus-data-2026 |
| S3_INPUT_PREFIX | incoming/ |
| S3_PROCESSED_PREFIX | processed/ |
| S3_RESULTS_PREFIX | results/ |
| LAMBDA_FUNCTION | claimshield-s3-processor |
| CLAIMSHIELD_API_URL | https://claimshield-nexus-api.vercel.app |

Set `CLAIMSHIELD_INTERNAL_TOKEN` on Lambda **and** FastAPI to the same value. Push Lambda code/env with `infra/lambda/claimshield-s3-processor/update_env.py` from a machine that already has AWS credentials. The API host needs `s3:GetObject` and `s3:ListBucket` on `incoming/`, and `s3:PutObject` on `processed/` and `results/`.

Upload a **full extract** (member, provider, claim or claims, claim_line, plus optional tables). Lambda fires per object; the last required CSV starts detection. Outputs go to `results/{batch_id}.json` and `processed/{batch_id}/`. Never write back to `incoming/`.

## Local run

```
cd backend
uv sync --extra dev
cp .env.example .env
# optional: CLAIMSHIELD_INTERNAL_TOKEN=<same as Lambda>
uv run uvicorn claimshield.api.main:app --reload --app-dir src --host 127.0.0.1 --port 8000

cd frontend
npm install
npm run dev
```

Open http://127.0.0.1:5173. Manager loads tiny/seed 7 if the desk is empty.

## Tests we rely on

```
cd backend
uv run pytest tests/test_aws_ingest.py tests/test_lambda_s3.py tests/test_config.py tests/test_workspace.py tests/test_rank.py tests/test_auth_api.py
```

## Domain promises we keep

- Recommend only. Escalate to State Medicaid PI.
- Payment suspension is the state’s call and needs manager approval.
- LEIE = NPI plus name plus exclusion date.
- Product language: “Potential FWA pattern requiring investigation.”

## Deploy notes

Vercel Python uses `backend/app.py` (sys.path insert of `src`). `CLAIMSHIELD_DATABASE_URL` is sqlite under `/tmp`. `CLAIMSHIELD_AUTO_SEED_BATCH=true` and `CLAIMSHIELD_DEMO_MODE=true` fill the desk on a cold start. Frontend `VITE_API_BASE` / production client points at `https://claimshield-nexus-api.vercel.app`.
