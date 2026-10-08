# ClaimShield Nexus: handoff (Oct 8, 2026, 10:15 PM IST)

Work was stopped at Panshul's request. This file lists what is merged, what is pushed but not merged, and what is left, in priority order.

## 1. Merged into `main`

- **PR #1, frontend redesign** (merge commit 949472f). Acentra green theme, Recharts 3 charts, a Cytoscape + fcose network graph, and a rebuilt dashboard. The landing page and flow are unchanged. `frontend/API_GAPS.md` lists what the UI still needs from the API. `frontend/src/components/network/graphModel.ts` `normalizeNetwork()` reads the new network fields as optional.
- **PR #2, trained risk models** (merge commit 5ed9c63).
  - A discrete-time monthly hazard model gives 30/60/90-day risk, monotone by construction. A calibrated logistic model gives P(confirm). Both were trained on a 15-month, 24-world synthetic panel, and the artifact is `data/models/risk_model.json`. Retrain with `make train`.
  - A rolling-origin backtest covers 5 held-out worlds. On it, 30-day PR-AUC is 0.482 (0.194 for the old heuristic) and P(confirm) PR-AUC is 0.952 (0.801 for the old heuristic). See `docs/MODEL_CARD.md`.
  - 98 backend tests passed.

## 2. Pushed but NOT merged: branch `handoff/backend` (this PR)

There are 13 commits on top of 5ed9c63, rebased onto it by the previous session:

1. Split case helpers, decisions and network out of `workspace.py`.
2. Return typed, evidence-carrying links on the case network.
3. Require manager approval for escalations and enforce decision ownership.
4. Reject missing CSRF headers, persist refresh-reuse revocation, and audit failed logins.
5. Match exclusions on NPI plus name, or name, DOB and address, inside the exclusion window.
6. Align the network API with the web client, and add entity summaries, decision options and session status.
7. Count priority-override hours against capacity and report expected value in dollars.
8. Base detectors on volume, paired trips, member-level opioid fills and coding bypasses, and validate brief citations.
9. Fix ruff findings and strict mypy errors.
10. Treat scikit-learn as untyped for mypy and fix lint from the rebase.
11. Apply ruff format.
12. Install the backend image from the committed `uv.lock` with `uv sync --frozen`.
13. Remove the superseded plan draft, document the network API (`docs/NETWORK_API.md`), and correct the READMEs.

Plus this handoff commit (docs only).

**Not verified after the rebase.** The full pytest, ruff and mypy run was interrupted, so do this first:

```bash
cd backend
uv sync --frozen
uv run pytest -q
uv run ruff check src tests
uv run ruff format --check src tests
uv run mypy src
```

If those are green, merge this PR with a merge commit so each commit stays separate. If anything fails, check first for conflicts between the model code from PR #2 (risk fields and heuristic fallback) and the split-out case modules from commit 1.

## 3. CI workflow (must be added by hand)

The bot's GitHub token cannot push `.github/workflows/*`. The file is in `docs/ci/ci.yml.txt`. On GitHub, go to Add file, then Create new file, name it `.github/workflows/ci.yml`, paste the contents and commit. It runs backend uv sync --frozen, ruff, mypy and pytest, and frontend npm ci, lint and build.

## 4. Left to do, in priority order

### A. Frontend wiring to the new backend (needed for the "network linkage" fix to show)
- Read the new typed network edges with evidence (shared contact, owner, TIN, address hubs, referral direction and count), `in_case` and finding IDs per node, and entity summaries. See `docs/NETWORK_API.md` and `frontend/API_GAPS.md`. Clicking a node or edge should open its claims and findings.
- Replace the hard-coded decision list with the decision-options endpoint. Escalation needs manager approval. Allow follow-up decisions on `needs_evidence` and `monitor`.
- Show `risk_factors` and `p_confirm_factors` (top factors) on the case page, and `model_version`, `calibrated` and `score_kind` wherever risk is shown.
- Replace the 25/50/75 P(confirm) placeholder bands with <50%, 50–90%, 90–99% and ≥99% (calibration is over-confident in the middle).
- `/auth/me` now returns 200 for anonymous users, so drop the 401 handling that logged a console error.
- Show the harm-lane hours counted against capacity, and EV in dollars.
- Then run `npm run lint` and `npm run build` in `frontend/`.

### B. Remaining audit items (full list in `docs/review/AUDIT.md`, section h)
Done or mostly done by the commits above: P0 items 3, 4, 6, 7, 8 (minus TS `strict`), 9 (partly), 10 (detectors), and the backend half of 5. **Not confirmed done**, so check them:
- P0-1: relabel remaining heuristic copy where the trained model isn't used (the fallback path).
- P0-2: hooks above early returns in `ManagerQueuePage.tsx` (may already be fixed by PR #1; run lint).
- P0-8: enable TypeScript `strict`.
- P0-9: template assets, root `pytest.ini`, the stale `data/generated/tiny`, rebrand to "student prototype for the Acentra Health Hackathon (PS3)", and ADRs copied into `docs/adr/`.
- P0-11: a minimal evaluation page or README section (per-scheme recall, precision at capacity across seeds). `docs/MODEL_CARD.md` covers part of it.
- P1-12 to P1-20: synthetic NPI format `NPI-SYN-…`, domain wording fixes (no MAI column in the Medicaid MUE file, NCCI attribution, the Utah line in `01_PS3_research_brief.md:162`, pejorative labels), a good-cause badge, SLA from lead receipt, brief citations of graph evidence, chart axes and units, a 404 route, the worklist N+1, and tests (route × role matrix, a Playwright smoke test).
- P2-21 to 27: optional.

### C. Domain rules to respect (from `docs/review/DOMAIN_AUDIT.md`)
- The product recommends only. Escalation goes to the State Medicaid agency's program integrity unit, not directly to the MFCU.
- Payment suspension is the state's decision and needs manager approval.
- LEIE matching needs NPI plus a name check and the exclusion date.
- CMS uses a one-sided 90% CI lower bound.
- NetworkX Leiden needs `metric="modularity"`.

### D. Final pass
- Run everything (scripts in `docs/review/scripts/`: `start_api.sh`, `start_web.sh`, `seed_demo.py`, `screens.py`), take fresh screenshots of every page, and update the README screenshots.

## 5. Reference files added in this PR
- `docs/review/AUDIT.md` is the full technical audit and the 27-item fix list.
- `docs/review/DOMAIN_AUDIT.md` is the Medicaid FWA domain audit (21 must-fix, 33 minor).
- `docs/review/DESIGN_SYSTEM.md` and `docs/review/tokens.css` hold the Acentra green tokens (#2bbc2b, #209b47, #1c873e, ink #042126; Inter and Roboto Mono).
- `docs/review/REFERENCES.md` collects dashboard and graph design references.
- `docs/review/scripts/` holds the audit, probe and screenshot scripts.
- `docs/ci/ci.yml.txt` is the CI workflow to add by hand.

## 6. Open questions for the team
- The submission deadline.
- Whether Acentra supplies a PS3 dataset. Everything is trained and tested on synthetic data so far.
