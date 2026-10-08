# ClaimShield Nexus: technical audit

- **Repo:** `panshularora/ACENTRA_ClaimShield_Nexus`, branch `main`, head `a9679fa` (42 commits). Read-only: nothing committed or pushed, and `/workspace/claimshield-ui` was not touched.
- **Audited:** 8 Oct 2026, 19:50–20:20 IST, on the shared box (Linux; Python 3.14 venv picked by uv; Node 20.19).
- **Folded in:** the Research Lab domain audit (`/workspace/claimshield-domain-audit/DOMAIN_AUDIT.md`, 21 must-fix and 33 minor items). Its items are tagged **[RL-Mn]** / **[RL-mn]**. Items I re-checked in code or in the running app are marked *verified*.
- **Rule for this report:** nothing is called "working" unless I ran it. Untested items say so.

Evidence:
- Logs: `/workspace/claimshield-review/logs/` (`pytest*.log`, `ruff*.log`, `mypy.log`, `npm_*.log`, `probe_*.txt`, `case_packs.json`, `quick_eval.txt`, `browser_report*.json`, `uv_lock_drift.diff`).
- Screenshots: `/workspace/claimshield-review/screens/baseline/` (62 PNGs).
- Scripts: `/workspace/claimshield-review/scripts/`.

---

## (a) State of the product

ClaimShield Nexus is a working vertical slice. Here is the part I ran end to end:

1. A seeded synthetic Medicaid-like generator (47 providers, 120 members, 2,767 claim lines, 28 planted schemes plus 2 hard negatives).
2. About 20 deterministic rules, three peer-anomaly detectors and three graph detectors, giving 35 alerts.
3. Union-find grouping into 16 cases.
4. A five-factor weighted score with a harm lane and a 0/1 knapsack on investigator hours.
5. A template brief whose sentences carry citation chips.
6. A decision bar that writes a hash-chained audit event and drafts a precedent proposal for approval.
7. Cookie-JWT auth with RBAC and audited member unmasking.

Backend tests pass and the frontend builds. Lint fails on one rules-of-hooks error, ruff reports 297 issues, and strict mypy reports 81 errors.

The headline "intelligence" is hand-set, not learned:
- P(confirm) is a fixed logistic formula.
- The 30/60/90 "discrete-time hazard" is `1-(1-m)^k` with `m = 0.05 + 0.28·p + 0.03·harm`.
- There is no LLM, no ML model, no evaluation report, no FHIR adapter and no entity resolution.

The UI copy nonetheless says "AI recommends", "survival of the pattern" and "held out of model training". The network panel has no three.js left: it is a static SVG with a fixed arc layout. It shows 20–35 unlabelled provider dots that are mostly referral noise, a single "N members" blob, and one edge colour. It omits the shared-contact links that actually justify the ring alert. Nodes are not tied to findings, claims or brief citations.

The domain audit adds credibility problems a payer judge will catch:
- Harm 4 ("member safety") is given to after-death and LEIE hits.
- Escalation defaults to an MFCU referral with no manager approval.
- LEIE matching is NPI-only; the seed contains a name mismatch that still becomes a harm-4 case.
- Several detectors would fire on normal fee-schedule billing.
- The UI carries Acentra branding and Acentra's tagline.

## (b) Built vs plan (M1–M16, X1–X18, PS3 requirements)

Legend: ✅ built and exercised by me · 🟡 partial or heuristic · ❌ not built.

| ID | Plan item | Status | Evidence |
|---|---|---|---|
| M1 | Generator, planted schemes, rings, hard negatives, GT kept separate | ✅/🟡 | `synth/` generates S01–S21, G1–G3, C1, HN1–2. Deterministic run-to-run on this box. **But the committed `data/generated/tiny/*.csv` does not match what the current generator produces for seed 7** (every table differs; `evv_visit` has 221 rows committed vs 453 regenerated). `ground_truth.csv` sits in the same folder as the extract. |
| M2 | Adapters: generator, canonical CSV, FHIR R4 | 🟡 | Generator plus S3/CSV ingest (`ingest/csv_extract.py`, `s3_ingest.py`; covered by tests, but I did not call AWS). **No FHIR.** |
| M3 | Data-quality report per load | 🟡 | `load_report` has table row counts only. No null rates, rejected rows or stop condition (`batch_reject_stop_pct` is defined in config but unused). Not shown in the UI. |
| M4 | Rules as versioned data linked to policy | 🟡 | `data/reference/rules.yaml` plus `rules/catalog.py` stamp a version and `policy_ref`, but rule logic is hard-coded in `rules/engine.py` (540 lines). There are opaque policy tags [RL-m8] and NCCI misattributions [RL-M12]. |
| M5 | Peer anomaly: robust z, IQR fence, ECOD/IForest | 🟡 | Robust z and IQR fence with peer-group widening (`anomaly/peer.py`). No ECOD or Isolation Forest (scikit-learn is installed but never imported). |
| M6 | Temporal checks | ✅ | Daily minutes cap, inpatient overlap, ambulance "overlap" (FP-prone, [RL-M8]). |
| M7 | Graph: shared address/owner/phone/bank, referral, Leiden, centrality | 🟡 | `graph/build.py` builds shared location, TIN, owner, contact and referral links. Pagerank is used only to pick the ring "leader". `communities_for` (Leiden with Louvain fallback) is **dead code**, and `build_cases` ignores its `communities` argument (`cases/builder.py:49`). |
| M8 | Entity resolution (deterministic + fuzzy) | ❌ | `rapidfuzz` is never imported. Owner/LEIE matching is exact lowercase name or NPI only [RL-M4]. |
| M9 | N alerts → M cases | ✅ | 35 alerts → 16 cases on seed 7. Can merge unrelated schemes: one case holds after-death, doctor shopping, sex, POS, clone and referral [RL-M9]. |
| M10 | Capacity knapsack + harm override + needs-evidence lane | 🟡 | Built (`pipeline/service.py:39-81`), but **queued work exceeds capacity: 60 h queued vs 40 h capacity**, seen in the running app (`08_manager_queue_top.png`). |
| M11 | Cited brief with validator and template fallback | 🟡 | Template only. The validator is hard-coded `dropped: 0` (`cases/workspace.py:691`) [RL-M16]. No LLM path (`llm_*` settings are unused). |
| M12 | Decision → hash-chained audit → label → precedent draft | ✅ | Ran it: a decision writes `case.decide` plus `wiki.propose`, and the chain verifies intact. State-machine bugs are in (d). |
| M13 | Auth, server-side RBAC, masking with logged unmask | ✅/🟡 | Argon2id, JWT cookies, refresh rotation, rate limit, RBAC, unmask audited. Security bugs are in (e). |
| M14 | Evaluation report (rules vs ML vs combined, unseen variants, top-K FP) | ❌ | Nothing in the repo or UI. My quick check is in (g). |
| M15 | 30/60/90 discrete-time hazard, calibrated, backtested | ❌ (heuristic) | `pipeline/service.py:27-36` is a formula, not a model [RL-M1]. See "Real model option" below. |
| M16 | Knowledge wiki: pages, change log, approvals | 🟡 | Precedent proposals and approve/reject only. No provider, scheme or rule pages. Precedent matching exists. |
| X1 | Rules as data | 🟡 | As M4. |
| X2 | What-if simulation | ❌ | — |
| X3 | Entity resolution | ❌ | As M8. |
| X4 | Alert-to-case consolidation | ✅ | Plus the provenance/lineage panel. |
| X5 | Capacity-aware selection | 🟡 | Knapsack runs on the composite score, not EV [RL-M18]. |
| X6 | Action ladder | 🟡 | Exists but legally mis-specified [RL-M5]. |
| X7 | Sampling + overpayment CI | ❌ | (Fact-check note: if built, use the one-sided 90% lower bound.) |
| X8 | Displacement monitoring | ❌ | — |
| X9 | Rule suggestions | ❌ | — |
| X10 | "What would clear this case" | 🟡 | Static evidence-gap text per alert kind (`workspace.py:115-126`). |
| X11 | Fairness / provider-disruption check | 🟡 | Peer-group confidence only. `sole_community` is generated but never shown [RL-M6]. No flag-rate table. |
| X12 | Grounding check | ❌ | Hard-coded, as M11. |
| X13 | Drift monitoring | ❌ | — |
| X14 | Recovery/outcome tracking | ❌ | Investigation seed rows only, internally inconsistent [RL-m26]. |
| X15 | SLA / case ageing | 🟡 | 45-day clock from the run date, so every case shows "45d" [RL-M19]. |
| X16 | "Why A ranks above B" | 🟡 | `why_rank` text plus factor bars, and a compare checkbox in the queue. |
| X17 | Referral packet export | ❌ | — |
| X18 | Prepay/postpay switch | ❌ | Future in the plan anyway. |

**PS3 requirement summary:**

| Requirement | Status | Note |
|---|---|---|
| Rules | ✅ | Built. |
| Anomaly | 🟡 | Statistical only. |
| Graph / network | 🟡 | Detection works; the network UI is weak, see (g). |
| 30/60/90 prediction | 🟡 | Heuristic placeholder. |
| Capacity-aware SIU queue | 🟡 | Over-commits capacity. |
| Explainable evidence-cited briefs | 🟡 | Template, with a fake validator. |
| Human decision loop / audit | ✅ | Built, with state-machine and approval gaps. |

## (c) Test, build and lint results (all run by me)

| Check | Command | Result |
|---|---|---|
| Backend install | `cd backend && uv sync --extra dev` | OK (Python 3.14 venv). **Side effect: rewrote `backend/uv.lock`** (+88/−26). The committed lock lacks the `aws` extra (boto3), so `uv lock --check` fails and `uv sync --frozen`/CI would break. I saved the diff to `logs/uv_lock_drift.diff` and restored the file to HEAD; the working tree is clean. |
| Backend tests | `uv run pytest` | **64 passed, 0 failed**, 57 warnings, 148 s. The repo's own `addopts=-q` doubled with root `pytest.ini` hides the summary line, so I re-ran with `-o addopts=""`. Warnings: the test JWT key is 31 bytes (`InsecureKeyLengthWarning`, `tests/conftest.py:23`) and Starlette's TestClient is deprecated. The slowest single setup took 30 s because Argon2 hashing of 7 seed users runs per test client. |
| Ruff lint | `uv run ruff check src tests` (config in pyproject) | **297 errors** (exit 1): 144 E501, 95 B008, 18 RUF046, 10 E741, 6 B007, 6 UP037, 3 I001, 2 F401, 2 F841, and more. 30 are auto-fixable. Real bugs/dead code among them: `workspace.py:527` (unused `kinds`), `wiki/service.py:5` (unused `UTC`), `synth/schemes.py:19` (unused import), `anomaly/peer.py:75` (unused loop variable). |
| Ruff format | `ruff format --check` | **25 files would be reformatted.** |
| Mypy | `uv run mypy src` (`strict = true` in pyproject) | **81 errors in 26 files** (39 type-arg, 14 arg-type, 12 import-untyped, …). The plan's "mypy --strict must pass" gate is not met. |
| Frontend install | `npm install` | OK, 0 vulnerabilities. |
| Frontend build | `npm run build` (`tsc -b && vite build`) | **Passes.** Warning: single JS chunk of **1,361.8 kB** (379.5 kB gzip); three/r3f/drei are bundled into every route although only the landing and login use WebGL. |
| Frontend lint | `npm run lint` (oxlint) | **Fails (exit 1): 1 error, 7 warnings.** Error: `ManagerQueuePage.tsx:198`, `useMemo` called after an early return (rules-of-hooks). Warnings: set-state-in-effect at `ManagerQueuePage.tsx:98` and `DecisionBar.tsx:100`; exhaustive-deps at `ClaimsTable.tsx:31,50` and `ManagerQueuePage.tsx:233`; only-export-components at `router.tsx:12` and `AuthProvider.tsx:53`. |
| Frontend tests | — | **None exist** (no Vitest, no Playwright e2e). |
| TS strictness | `tsconfig.app.json` | **`strict` is not enabled** (the plan required strict plus `noUncheckedIndexedAccess`). `src/api/types.ts` (530 lines) is hand-written; there is no openapi-typescript generation, which TS 6 breaks per the fact-check notes. |
| CI | — | **No `.github/workflows`**, no pre-commit and no Makefile `ci` target. |
| Docker | `docker compose up` | **Not run** (no Docker on the box). Postgres mode is untested. Note that `backend/Dockerfile` does not copy `uv.lock` and runs `uv sync --no-dev`, so the image build is unpinned. |

## (d) Bugs and broken flows (found while clicking through and probing)

Case IDs refer to the current running DB, run `RUN-7FIVS5NCAH`. Probe evidence is from an earlier run in `logs/probe_security.txt`; I reset the DB afterwards for a clean demo.

1. **Lint-breaking hook-order bug.** In `frontend/src/features/queue/ManagerQueuePage.tsx:180-198`, `if (!user) return null; if (!canQueue) return …;` comes before `useMemo`. React can throw "rendered fewer hooks" when auth state flips.
2. **Capacity over-commit.** `backend/src/claimshield/pipeline/service.py:47-58` puts every harm ≥ 4 case in the harm lane but subtracts only `min(harm_hours, 35%·capacity)` from capacity. Seed 7 gives harm 34.5 h + selected 25.5 h = **60 h against 40 h**. The UI says "Applied run 40.0h · queued work 60.0h" with no warning (`08_manager_queue_top.png`). The test name `test_harm_lane_does_not_consume_capacity` (`tests/test_detection_quality.py`) codifies the behaviour. *Verified; same as [RL-M18].*
3. **Decision state machine.** `cases/workspace.py:990-1009` has no assignment check and no terminal-state check. Probes (all HTTP 200):
   - `investigator2` decided a case owned by `investigator`;
   - the same case was then escalated, then dismissed after escalation.
   - Also `approved_by` is always None (`:1018`), and nothing requires manager approval for escalations [RL-M5].
4. **Frontend locks the case after any non-open status.** `WorkspacePage.tsx:122` sets `closed = data.status !== "open"`, so a case in `needs_evidence` or `monitor` can never get a follow-up decision from the UI (seen on `CASE-2J26MIBLIL`, `53_ws_decided_decide.png`). The backend allows it, as above.
5. **No length limit on decision or override reasons.** `api/routers/cases.py:32,43` declare `reason: str` with no max. A 200,000-character reason was accepted. It was copied into the precedent body, and the proposal detail page then laid out **1.8 million px wide** (Chromium crashed taking a full-page screenshot in the probe run). Add `max_length` (e.g. 4,000) plus CSS `overflow-wrap:anywhere`.
6. **Timeline header misaligned.** `TimelinePanel.tsx:17-20`: the kicker and `<h2>` are direct children of a flex `space-between` header, so "Timeline" floats to the far right (`19_ws_ring_harm_timeline.png`). Wrap them in a `<div>` as `NetworkPanel` does.
7. **Unknown routes and cases.**
   - There is no `notFoundComponent`; `/no-such-route` shows TanStack's bare "Not Found" plus a console warning (`62_unknown_route.png`).
   - An unknown case ID fires **10** 404 requests (5 queries × `retry:1`) and shows the raw "case not found" string (`61_ws_unknown_case.png`).
8. **Network node click.**
   - Only provider nodes open anything (`WorkspacePage.tsx:106-108`); member, owner and facility clicks do nothing.
   - The drawer shows the raw provider JSON, with no link to that provider's claims or alerts (`22_ws_ring_harm_network_node_clicked.png`).
   - Focusing an SVG `<g tabIndex=0>` draws a black rectangle (no focus style).
   - Keyboard Enter on the aggregated `__members__` node calls `onSelect("__members__")`, unlike click (`NetworkGraph.tsx:166-172`).
9. **Edge filters leave orphans.** Unticking edge kinds hides edges but not the nodes that become unconnected (`59_ws_ring_backlog_network_structural_only.png`).
10. **FindingsPanel hides evidence.** `collapseAlerts` (`FindingsPanel.tsx:14-29`) merges alerts by `rule_id`. Two G-RING alerts with different rings show only the first one's evidence, and clicking opens only the first alert.
11. **Timeline refs go nowhere.** `WorkspacePage.tsx:100-104` ignores `referral:`, `investigation:` and `stay:` refs, so clicking those timeline rows does nothing. Inpatient stays are listed for every member in the case with no date-window filter (`workspace.py:798-815`).
12. **Unmask toggle writes extra audit events.** It re-fetches claims, timeline and network together (`WorkspacePage.tsx:60-74`), so one toggle writes three `member.unmask` events, including for tabs never opened.
13. **Worklist N+1.** `InvestigatorCasesPage.tsx:60-67` calls `GET /cases/{id}` for every desk case in parallel. Each call recomputes rank factors over all peers server-side.
14. **Inconsistent numbers on screen.**
   - The Severity factor bar shows 80% next to "Severity 3", because `rank.py:91` uses `max(harm, severity)/5` on a 1–4 scale [RL-m6].
   - The brief prints the 30/60/90 values as raw floats ("0.369 / 0.602 / 0.749", `workspace.py:615-618`) while the UI shows percentages.
   - "Expected value $16,367" on a $2,310 case: the value is dominated by `250·harm·members` pseudo-dollars (`queue/knapsack.py:4-7`) [RL-M18].
   - The lane chart says "Monitor" (`three/QueueScene.tsx:8`) where the lanes say "Tracked backlog".
15. **Brief cites boilerplate.** Limitations and "recommended action" sentences cite `metric:harm` ("case metrics"). The graph evidence (edge kinds, linked NPIs) is never mentioned in the brief.
16. **Doctor-shopping alerts carry no evidence lines.** They have `line_ids=[]` (`rules/engine.py:317-341`), so the drawer and brief say "0 lines" (`10_manager_queue_case_drawer.png`) [RL-M9].
17. **Console noise on every page.** Each page logs a 401 on `GET /api/v1/auth/me` before login (expected but noisy; `/me` could return 200 `null`) and a `THREE.Clock` deprecation warning. No other console errors or failed requests appeared on the routes I captured (`logs/browser_report.json`).

## (e) Backend and API issues

**Security and auth:**
- **CSRF bypass.** `api/deps.py:90-91`: when `cookie_secure` is false (the default and the demo setting), a request **without** an `X-CSRF-Token` header skips the check. Probe: `POST /cases/{id}/assign` with no header → 200. SameSite=strict cookies mitigate this, but the check is effectively off.
- **Refresh-token reuse revocation never persists.** `auth/service.py:167-173` sets `revoked_at`, flushes, then raises `Unauthorized`. `get_db` (`api/deps.py:40-52`) rolls back on any exception, so the revocation is lost. Probe: replaying an old refresh token → 401 "reuse detected", but the legitimate session refreshed afterwards → **200**.
- **Insecure defaults.** `core/config.py` defaults to `demo_mode=True` and `jwt_signing_key="dev-only-change-me"`, with no startup guard. In demo mode, `GET /api/v1/meta` (unauthenticated) returns every demo password (`routers/health.py:21-26`). Fine for a judged demo, but production must fail closed.
- **Failed logins are not audited** (`auth/service.py:121-124`). The rate limiter is in-memory and per process (5 per 60 s per ip+email; probe got 401×4 then 429).
- **No segregation of duties.** A manager can approve the precedent drafted from their own decision (probe → 200; `wiki/service.py:215-240`).
- **Evidence endpoint leaks outside the case.** `GET /cases/{id}/evidence/provider:{any}` returns any provider, not just case parties (`workspace.py:480-484`). Minor.

**RBAC matrix observed** (GET; 200 = allowed):
- Analyst cannot see the queue or cases (403) but can approve precedents.
- Auditor can read cases and claims but gets masked members even with `unmask=true`.
- Admin (`admin:*`) gets every permission, including unmask and decide.
- Investigators can read and decide **any** case; there is no object-level ownership.

**PHI masking:**
- Masking is applied to names, and unmasking writes `member.unmask`.
- The masked payload still carries the full `member_id` (`workspace.py:159-168`) and network member-node IDs.
- Synthetic IDs, but the plan's "minimum necessary" rule would hash or tokenise them.

**Correctness:**
- **Validator is fake** (`workspace.py:691`) [RL-M16].
- **`rank_pack_for_case` recomputes at request time** with `date.today()` (`queue/rank.py:514-527`), so displayed factors can drift from the factors the lanes were packed with.
- **Every case gets the same SLA due date**, `run_date + 45` (`pipeline/service.py:225`) [RL-M19].
- **Recompute creates new case IDs** each run (`new_id("CASE")`), so decisions on the previous run's cases are orphaned from the new queue (the UI follows the newest run).
- **Unvalidated `approve` body.** `POST /decisions/{id}:approve` and `/wiki/proposals/{id}:approve` accept an optional body; the note is unbounded.

**Error handling:**
- Domain errors map to RFC 9457 problem JSON, which is good.
- FastAPI's own 422s use a different shape (`{"detail":[…]}`).
- There is no catch-all 500 handler.

**Data layer:**
- `Base.metadata.create_all` at startup (`api/main.py:31`). Alembic is a dependency but has no migrations.
- `append_event` reads the last row and then writes, with no lock (`audit/service.py:28-30`). Concurrent writers can fork the chain.
- `/audit` and `/audit/{seq}` rebuild and re-verify the whole chain on every call (O(n)).

**Performance (fine at tiny size):**
- Run summaries count alerts and cases with `len(scalars().all())` (`routers/batches.py:114-129`).
- The network referral loop does a `session.get` per node (`workspace.py:950-957`).

## (f) Code-quality issues judges will notice

**Dead and template files:**
- `CLAIMSHIELD_PLAN_DRAFT.md` (1,325 lines, superseded; contains the MAI/eCAMS errors; linked from `README.md:13`) [RL-m20].
- `IDEATION_AND_IMPROVEMENTS.md`.
- `frontend/src/assets/{hero.png,react.svg,vite.svg}` and `frontend/public/icons.svg` (unreferenced Vite template assets).
- Root `pytest.ini` duplicates the pyproject config.
- `graph.communities_for` and the `build_cases(communities=…)` parameter are dead.

**Misnamed modules and stale copy:**
- `src/three/NetworkGraph.tsx` and `src/three/QueueScene.tsx` contain no three.js; they are SVG.
- READMEs still say "3D network / orbit the 2-hop neighbourhood / 3D lane towers" (`frontend/README.md`, root README "scroll-driven Three.js story" is accurate only for the landing).

**Unused dependencies:**
- alembic, pandera, rapidfuzz, structlog, orjson, scikit-learn, httpx (runtime), email-validator (used indirectly by EmailStr; keep), python-multipart.
- Optional `ml` extra (lightgbm, shap, pyod) is never imported [RL-M2].

**Lockfile drift:** `uv.lock` is out of date with `pyproject.toml` (see c).

**Duplicated vocabularies:**
- `RULE_TITLES` and `KIND_LABELS` are hard-coded in `cases/workspace.py:69-114`, duplicate `data/reference/rules.yaml` and `rules/catalog.py`, and are duplicated again in `frontend/src/lib/format.ts` (labels drift; the queue drawer shows "referral monopoly" in lower case).

**Large modules:**
- `cases/workspace.py` (1,198 lines) mixes serialisation, briefing, network, timeline and decisions, and uses local imports to dodge an import cycle with `wiki/service.py`.
- `ManagerQueuePage.tsx` is 814 lines.

**Typing and lint:** see (c). Per-module READMEs are absent, and many public functions lack docstrings.

**Test gaps:**
- No API-route × role access matrix.
- No property tests (hypothesis is installed but unused).
- No validator tests (none exist), no network/timeline content tests, no frontend tests and no e2e.
- Nothing covers the CSRF, refresh-reuse, decision-ownership or reason-length bugs above.

**Repo and data hygiene:**
- The committed extract is stale versus the generator (b, M1).
- `ground_truth.csv` is committed next to the features.
- All exclusion DOBs are `1965-03-12`.
- Synthetic NPIs are 10-digit real-looking numbers (`synth/luhn.py`; README "pass Luhn" is wrong per [RL-M17]); the fact-check asks for the `NPI-SYN-` format.

**README accuracy:**
- Uses Windows `copy .env.example .env`.
- Says "held out of model training" (no model exists).
- "Docker: docker compose up" is untested here.
- Does not say that a manager must click "Load tiny run" (or `POST /batches`) before any queue appears.
- No architecture diagram, no screenshots, no "limitations" section.
- The ADRs in `/workspace/claimshield/docs/adr/` are not in the repo (repo `docs/` has only `AWS_INGEST.md`).

## (g) Frontend: network, graph and chart diagnosis

### What the API returns

`GET /api/v1/cases/{id}/network` (`workspace.py:822-987`):
- **Nodes** `{id, type, label, primary, risk?, specialty?, masked?, owner_kind?, facility_type?}`, with types provider, member, facility and owner. Only the primary node has `risk` (= p_confirm).
- **Edges** `{source, target, kind}`, with kinds `rendered`, `billed`, `at_facility`, `owns`, `referral`, `shared_location`, `shared_tin`.
- **Scope:**
  - all billing/rendering providers, members and facilities from the case's flagged lines;
  - then every provider sharing a location or TIN (when hops=2);
  - then owners;
  - then **every referral to or from any of those providers**;
  - then members are truncated to 20 if there are more than 80 nodes.

Measured on all 16 cases of seed 7 (`logs/probe_network.txt`):
- Graphs have 7–60 nodes and 9–127 edges, with no isolated nodes in the API data.
- A single-provider case pulls in **19–33 providers** (out of 47 in the whole extract), mostly via `referral` edges (20–41 per graph).
- `shared_location` is emitted as a clique: 28 edges for one address.

### Linkage gaps

These explain "no proper linkage":
1. **The ring's actual evidence is not drawn.**
   - The ring alerts' evidence says `edge_kinds: ["shared_contact","shared_owner","shared_tin"]` (ring backlog case `CASE-0QQXDVY8D5`, 6 NPIs), but the network endpoint never reads `contact_point`, so no `shared_contact` edge exists.
   - `shared_owner` appears only indirectly as `owner→provider` `owns` edges.
   - The frontend lists `shared_owner` and `shared_contact` in `EDGE_KINDS` (`NetworkPanel.tsx:6-16`) but never receives them.
2. **No node or edge is tied to a finding.**
   - Nodes carry no `alert_ids`, `rule_ids`, flagged-line counts, flagged dollars, or an "in this case" vs "context" flag.
   - Edges carry no evidence reference (claim line, referral count, ownership-link ID, contact hash), no weight and no date.
   - `referral` edges are deduplicated on a sorted key (`workspace.py:838`), so direction and volume are lost; that destroys the G-REF "concentration" story.
3. **The case's own NPIs are indistinguishable from context.** `case.entity_ids` (the 5–6 linked NPIs) is not echoed per node. In the UI all providers are identical green dots, and only the primary is labelled.
4. **No graph metrics.** Pagerank and communities computed in the pipeline (`graph/detect.py:151`, `graph/build.py:65`) are not persisted or returned.
5. **The brief and evidence drawer never cite graph objects.** There is no `edge:` or `node:` evidence kind in `evidence_item` (`workspace.py:456-510`).

### What the frontend renders

`three/NetworkGraph.tsx` (not three.js) renders a static 560×420 SVG:
- **Fixed layout** (`layout`, lines 19-71): providers on one arc (r = 128), owners on a short arc that overlaps it (r = 88), facilities at r = 196, and members scattered by hash. Position encodes only node *type*, never connectivity.
- **Member blob.** When there are more than 8 members, all of them collapse into one "N members" node pinned at (78, cy) (`compactPack`, lines 85-111), so every rendered/billed edge converges on one point.
- **Labels only on the primary node, the member blob, and hover/click** (line 176). The browser measured **2 text labels for 37 nodes and 91 lines** on the ring harm case.
- **Edges are plain lines in two greys/greens** ("hot" if referral, owns or shared). There is no per-kind colour, no edge legend, no arrowheads, no width by volume and no labels. The legend covers node types only.
- **Clicks.** Only provider nodes open the drawer (raw JSON). Filters do not prune orphaned nodes. The `reduced` prop is unused, and the header count ("51n · 111e") does not match what is drawn (37 nodes after aggregation).

Screens: `20_…_network.png`, `21_…_network_svg.png`, `31_ring_backlog_network_svg.png`, `59_…_structural_only.png`.

### Charts

| Component | Data | Implementation | Axes / labels / units |
|---|---|---|---|
| `FactorBars` (`features/queue/FactorBars.tsx`) | `rank_factors` {severity, exposure, member, evidence, urgency, composite, weights} | CSS `width:%` bars | Labels and % shown. Shows raw factor scores, not weighted contributions (`weights` is available but unused); no scale explanation; the severity scale bug is in (d)14. |
| `PeerCompare` / `PeerRange` (`PeerCompare.tsx:58-80`) | alert `evidence` {provider_value, peer_q1, peer_median, peer_q3, peer_min/max, robust_z, fence, peer_group} | Three absolutely positioned spans, `aria-hidden` | **No axis, tick labels or units**, and no fence line, although `fence` and `peer_min/max` are in the payload. The numbers sit in a separate `<dl>`. |
| `EvidenceBar` (`components/EvidenceBar.tsx`) | `evidence_strength` | CSS bar plus % | No threshold marker for the 0.40 floor that drives the needs-evidence lane. |
| `TimelinePanel` | `/timeline` events {ts, kind, flag, ref, title, detail, entity_id} | Vertical `<ol>` list | Not a chart. No time axis or gaps; raw ISO dates; header bug (d)6. |
| `QueueScene` (`three/QueueScene.tsx`) | hours by lane | Real SVG horizontal bar chart with hour ticks | **No capacity line.** The 40 h capacity vs 60 h queued is invisible; the "Monitor" label mismatch is in (d)14. |

### Data a better UI can use today, without backend changes

- Per case: `entity_ids` (case NPIs), `grouping.rule` and `grouping.text`, `grouping.comparison_peers_held_out`, and `alerts[].entity_id`, `alerts[].evidence.peer_ids`, `.edge_kinds`, `.ring_id`, `.pagerank`, `.n_providers`, `.enroll_dates`, `.top_referrer`, `.top_share`, `.hhi`, `.n_referrals`, `.owner_name`, `.line_ids`.
- From these the UI can:
  - highlight case NPIs vs context;
  - draw the ring hull;
  - label edges with the alert that relies on them;
  - make referral concentration a weighted edge from `top_referrer` (top_share);
  - connect node clicks to `alerts.filter(a => a.entity_id === id || a.evidence.peer_ids?.includes(id))` and to claims rows where `rendering/billing_provider_id === id`.
- Claims rows carry `rendering_provider_id`, `billing_provider_id`, `member.member_id`, `signals[]` and `paid`. That is enough to aggregate flagged dollars and lines per provider node, and to link member nodes to claim lines.
- Timeline events carry `entity_id` and `ref`, which allows brushing between the timeline and the graph.

### Backend additions needed for proper linkage (small)

1. Emit `shared_contact` edges (provider–contact hash, or provider–provider) from `contact_point`.
2. Emit a `location` node instead of `shared_location` cliques.
3. Keep referral direction plus a `count` attribute.
4. Add per-node `in_case`, `alert_ids`, `n_flagged_lines`, `flagged_paid`, `pagerank` and `community`.
5. Add per-edge `evidence_ref`.
6. Scope referral expansion to case NPIs (or top-k by volume), not every neighbour.
7. Add `node:`/`edge:` evidence kinds so brief sentences can cite them.

**Effort:** about 0.5 day backend plus about 1 day frontend, using a force-directed layout (d3-force, already a common dependency; or Cytoscape as planned) with edge colours per kind, a legend, case-NPI emphasis, labels and click-through to the alert, claims and drawer.

### Quick detection check (not in repo; M14 is missing)

`scripts/quick_eval.py` on tiny seed 7, using the same data the rules were written against:
- 27/28 planted fraud schemes have at least one provider in a case.
- 1/2 hard negatives was flagged.
- 22 of 26 flagged providers belong to a planted scheme.

This is in-sample and optimistic. It should be replaced by a proper evaluation across seeds and held-out variants.

## Real model option (item 1: P(confirm) and 30/60/90)

**Current state (verified):**
- `cases/builder.py:230-245`: `z = -2.0 + 2.4·evidence + 0.35·min(3, n_detectors) [+0.4 harm≥4] [+0.25 graph] [+0.5 prior]`, then a sigmoid.
- `pipeline/service.py:27-36`: `m = clamp(0.05 + 0.28·p + 0.03·harm, 0.02, 0.65)`, then `F(k) = 1-(1-m)^k`.
- Neither is trained or calibrated, and F30/60/90 is a deterministic re-expression of P(confirm) and harm.
- `test_discrete_hazard_is_monotonic` tests the formula, not a model.
- UI and docs call this a hazard, survival, "AI" and a trained model [RL-M1, RL-M2].

| Option | What | Effort | Risk |
|---|---|---|---|
| **A. Relabel (do regardless)** | Rename to "Priority score (heuristic, uncalibrated)". Hide F30/60/90 or label them "illustrative escalation index — not a model". Fix "survival" wording (the formula is a CDF). Remove "AI recommends", "held out of model training" and the unused ml extras. Update brief text (`workspace.py:615-618`), `LandingPage.tsx:55,70-79`, `ManagerQueuePage.tsx:320,503,602,623`, `WorkspacePage.tsx:200,268`, `components/CaseDrawer.tsx:62,70`, `lib/format.ts:85`, and both READMEs. | **2–4 h** | None. Honest, and matches the plan's own fallback (`CLAIMSHIELD_PLAN_DRAFT.md:398,869,1104`: an "uncalibrated" transparent score, with F30/60/90 hidden). |
| **B1. Trained P(confirm) classifier** | Label = case contains a ground-truth `is_fraud` entity (synthetic) or a substantiated investigation outcome. Features = detector kinds (one-hot), number of detectors, max/mean alert score, evidence strength, flagged dollars, members, graph flags, peer z. Train on many seeds (e.g. tiny/small seeds 1–40), test on held-out seeds **and** held-out scheme type S06 plus B-variants. Logistic regression (explainable coefficients) or LightGBM plus SHAP. Isotonic/Platt calibration on a validation fold; report Brier, a reliability plot, PR-AUC, and precision/recall at the knapsack capacity (top-K by hours). Store a `model_version` and model card; show "calibrated on synthetic data only". | **1.5–2.5 dev-days** (dataset builder 0.5 d, train/calibrate/eval 0.5–1 d, wire into `build_cases` + API + UI + tests 0.5–1 d) | Labels are generator-defined, so the model learns the generator (leakage). Mitigate with held-out scheme types and variants, and say so. Tiny alone has about 16 cases per seed, so many seeds are needed. |
| **B2. Discrete-time hazard for 30/60/90** | Person-period table: one row per provider-month (or case-month) up to the event or censoring. Event = first month a planted scheme becomes active, or confirmation of the provider (from `ground_truth.start/end` and investigation outcomes). Features use only data with `received_date ≤ t` (rolling 1/3-month aggregates, rule-hit counts to date, peer z, graph degree/pagerank, prior investigations). Model = logistic (or LightGBM) on person-period rows with month-since-origin terms; `F(k) = 1-∏(1-h_t)`. Rolling-origin backtest (train ≤ T, test T+1..T+3, several origins); calibration per horizon; enforce F30 ≤ F60 ≤ F90 (a property test). Needs the generator to span enough months and the `small` profile for event counts (tiny: 47 providers × ~12 months ≈ 560 rows, ~28 events — too few). | **2.5–4 dev-days** (generator time span and censoring 0.5–1 d, person-period builder with leakage tests 1 d, model + backtest + calibration 1 d, wiring/UI/model card 0.5–1 d) | Same synthetic-label caveat. Must define the event clearly on screen. Adds runtime (train offline, ship a pickled model or coefficients with a version). |
| **B3. Eval report (M14) shared by B1/B2** | Rules vs model vs combined; per-scheme recall on held-out variants; top-K false positives; flag rate by provider type/region; precision/recall at capacity. | **0.5–1 day** | Needed for honest numbers whichever option is chosen. |

**Recommendation.** Do **A now (P0)**. Do B1 and B3 if there are at least 3 working days before submission. Do B2 only if B1 lands, because it touches the generator. Otherwise present B2 as designed-not-built, with the ADR-003 text.

## (h) Prioritised fix list

Effort assumes one developer familiar with the repo. Each item names its source: **[Me]** = found in this audit, **[RL]** = Research Lab domain audit (Mn/mn = its item number).

### P0: must fix before submission

1. **Relabel the heuristics.** P(confirm), F30/60/90, "AI recommends", "model training", "survival", and the fake validator ("template; citations by construction"). Option A above. Files listed in that table plus `workspace.py:691` and `BriefPanel.tsx:116-118`. *2–4 h.* [RL M1, M2, M16; verified] [Me]
2. **Fix the lint error.** Move all hooks above the early returns in `ManagerQueuePage.tsx:180-233`; clear the 7 warnings. *30 min.* [Me]
3. **Escalation and decision workflow.**
   - Default escalate → records request / full investigation.
   - Relabel the ladder to "Refer to State Medicaid agency PI unit (for MFCU consideration)".
   - Remove suspension from investigators, or gate it behind a manager-recorded credible-allegation determination plus a good-cause warning.
   - Require manager approval (`approved_by`) for escalate/referral.
   - Enforce assignee or manager only, and terminal states.
   - Allow follow-up decisions on `needs_evidence`/`monitor` in the UI.
   - Files: `cases/workspace.py:42-62,990-1069`, `DecisionBar.tsx:28-64`, `WorkspacePage.tsx:122,358-385`, `LandingPage.tsx:93`.
   - *0.5–1 day.* [RL M5; verified] [Me d3, d4]
4. **Harm lane and capacity.**
   - Split "program-integrity override" (after-death, LEIE) from "beneficiary harm" (opioid pattern, inpatient overlap, impossible hours) in `cases/builder.py:38-39`.
   - Rename the lane.
   - Either count harm hours against capacity or show an explicit over-commit warning plus a capacity line on the lane chart (`pipeline/service.py:39-62`, `three/QueueScene.tsx`, `ManagerQueuePage.tsx:242-245,505-520`).
   - Rename EV to "priority value (unitless)", or split dollars and harm.
   - *0.5 day.* [RL M3, M18; verified] [Me d2, d14]
5. **Rebuild the network panel with linkage** (section g):
   - backend: `shared_contact` edges, location nodes, referral direction/count, per-node `in_case`/alert IDs/flagged $, edge evidence refs, scoped expansion;
   - frontend: force layout, edge colour/legend per kind, case-NPI emphasis and ring hull, labels, click → alerts/claims/drawer, orphan pruning;
   - add `node:`/`edge:` brief citations;
   - files: `cases/workspace.py:822-987`, `three/NetworkGraph.tsx` (move to `features/workspace/`), `NetworkPanel.tsx`.
   - *1.5 days.* [Me]
6. **Security quick fixes.**
   - Enforce CSRF whenever the cookie auth path is used (`api/deps.py:90-91`).
   - Commit the refresh revocation before raising (`auth/service.py:167-173`).
   - `max_length` on reasons and notes (`routers/cases.py:30-43`, `routers/wiki.py`, `routers/decisions.py`) plus CSS overflow-wrap.
   - Fail closed on the default JWT key when `demo_mode` is false (`core/config.py`).
   - Audit failed logins.
   - Block self-approval (`wiki/service.py:215`).
   - Add tests for each.
   - *3–4 h.* [Me]
7. **LEIE matching ladder.** NPI + name + DOB/address + DOS ≥ excl_date; check rendering providers and owners; fix the seed name mismatch (NPI 3178816421 "Austin Howard" vs "Lauren Long", *verified*); vary DOBs; owner name-only = "possible", not harm 4. Files: `rules/engine.py:286-314`, `graph/detect.py:238-278`, `synth/generator.py`. *3–5 h.* [RL M4; verified]
8. **Code-quality gates.**
   - `ruff check --fix` plus `ruff format`, then fix the remaining E501/B008. B008 is FastAPI `Depends`: add an `extend-immutable-calls` config rather than 95 edits.
   - Either fix the 81 mypy errors or scope strict mode to core modules.
   - Enable TS `strict`.
   - Add `.github/workflows/ci.yml` (backend: uv sync --frozen, ruff, mypy, pytest; frontend: npm ci, lint, build). I did not check whether the GitHub token can push workflow files.
   - Regenerate `uv.lock` (`uv lock`) and copy it in the Dockerfile.
   - *0.5–1 day.* [Me]
9. **Repo hygiene and README.**
   - Delete `CLAIMSHIELD_PLAN_DRAFT.md` and its README link, the template assets (`src/assets/*`, `public/icons.svg`), root `pytest.ini`, unused deps and dead `communities_for`.
   - Regenerate or remove the stale `data/generated/tiny`; move `ground_truth.csv` to a separate `labels/` folder.
   - Fix READMEs: no "3D network/towers", POSIX `cp`, the first-run "Load tiny run" step, limitations, screenshots, architecture.
   - Copy the ADRs into `docs/adr/`.
   - Rebrand from "Acentra Health SIU" to "student prototype for the Acentra Health Hackathon (PS3)"; drop the "Accelerating better outcomes" tagline and the eCAMS-as-fact copy (`index.html:7`, `Shell.tsx:43`, `LoginPage.tsx:64`, `LandingPage.tsx:8-17,116,127`).
   - *3–4 h.* [Me] [RL M15, m20, m33; verified]
10. **False-positive-prone detectors: relabel now, fix if time.**
    - Clone billing on identical paid amounts (`rules/engine.py:428-447`).
    - Ambulance "overlap" that is base + mileage (`:398-425`).
    - Doctor shopping pinned to the first prescriber, with no lines (`:317-341`): make it member-level and stop merging into provider cases (`cases/builder.py:41,137-142`).
    - Sex rule without the KX/CC45 bypass (`:345-349`).
    - Relabel *1–2 h*; real fixes *1 day*. [RL M7–M10; verified for engine lines]
11. **Minimal evaluation report (M14).** Per-scheme recall, hard-negative FP, precision at capacity, across 5–10 seeds; show it on a `/models` or README page. Start from `scripts/quick_eval.py`. *0.5–1 day.* [Me] [RL M1(c)]

### P1: strongly recommended

12. **Synthetic NPI format** `NPI-SYN-…` (or 9-prefixed, deliberately invalid); fix the README Luhn claim (`synth/luhn.py`, `generator.py`). *1–2 h.* [RL M17] [fact-check]
13. **Domain text fixes:**
    - MAI wording in PAPERS/plan (Medicaid MUE has no MAI; `data/reference/unit_caps.csv` also carries an `mai` column) [RL M13; verified column];
    - NCCI misattribution in `rules.yaml:6,51` [RL M12];
    - PTP indicator-0 gap text, `workspace.py:120` [RL M11];
    - Utah line in the research brief, `01_PS3_research_brief.md:162` [RL M14];
    - "confirmed_pattern" on non-substantiated decisions, `wiki/service.py:111` [RL M21];
    - pejorative labels ("mill", "padding", "doctor shopping", "clone"), `workspace.py:101-113`, `format.ts:55-62` [RL M20].
    - *3–4 h total.*
14. **Good-cause badge** from `provider.sole_community` in the case header and brief. *1–2 h.* [RL M6]
15. **SLA from lead receipt** (earliest alert/claim date), configurable (`pipeline/service.py:225`, `queue/rank.py:514-527`); fix the "CMS PIM UPIC" attribution in copy. *2–3 h.* [RL M19]
16. **Brief quality:**
    - cite graph evidence (ring members, edge kinds);
    - stop citing `metric:harm` for boilerplate;
    - format percentages;
    - add the full Limitations list from [RL M16];
    - either implement a real validator (resolve cite IDs, regex numbers) or keep the honest label.
    - *0.5 day.* [Me] [RL M16]
17. **Chart honesty:**
    - `PeerRange` axis/ticks/units plus fence and min/max;
    - FactorBars showing weighted contribution and weights, and severity /4 (`queue/rank.py:91`);
    - EvidenceBar 0.40 floor marker;
    - time axis on the timeline.
    - *0.5 day.* [Me] [RL m6]
18. **UX fixes:**
    - timeline header (`TimelinePanel.tsx:17-20`);
    - 404 route and unknown-case states (`router.tsx`, `WorkspacePage.tsx`; `retry: false` on 404);
    - FindingsPanel collapse losing evidence (`FindingsPanel.tsx:14-29`);
    - timeline refs that do nothing;
    - SVG focus outline;
    - "linked NPIs" → "linked providers" [RL m10];
    - "Monitor" vs "Tracked backlog" labels [RL m5].
    - *3–4 h.* [Me]
19. **Performance and correctness of the API:**
    - drop the worklist N+1 (return factors in the queue payload, `InvestigatorCasesPage.tsx:60-67`);
    - persist rank factors at run time instead of recomputing with `date.today()`;
    - count with SQL `func.count`;
    - lock the audit append (or use `SELECT … FOR UPDATE` on Postgres);
    - code-split three.js to the landing/login routes (`React.lazy`).
    - *0.5 day.* [Me]
20. **Tests:**
    - route × role access matrix;
    - CSRF/refresh/ownership/length regressions;
    - hypothesis knapsack vs brute force;
    - F30 ≤ F60 ≤ F90 property;
    - network pack content (contains `shared_contact` for ring cases);
    - Vitest for DecisionBar and NetworkGraph;
    - one Playwright smoke test of the judge path (the scripts in `claimshield-review/scripts/screens.py` are a starting point).
    - *1 day.* [Me]

### P2: if time allows

21. Entity resolution with rapidfuzz for owner/LEIE names (plan M8/X3). *1 day.* [Me]
22. Leiden communities persisted and shown (pass `metric="modularity"`/a backend per the fact-check note for NetworkX 3.7, or drop the dead code). *2–4 h.* [Me] [fact-check]
23. A data-quality report shown on load (null rates, rejected rows, stop rule using `batch_reject_stop_pct`). *0.5 day.* [Me]
24. Alembic migrations, or remove alembic; Postgres compose path tested once. *0.5 day.* [Me]
25. Recompute keeping case identity across runs (stable case keys from the group key) so decisions follow cases. *0.5 day.* [Me]
26. Masked payloads: tokenise `member_id`. *1–2 h.* [Me]
27. Remaining Research Lab minors (non-duplicate items):
    - m1–m4, m7–m9, m11–m19, m21–m25, m27–m32;
    - seed realism: m25, m26, m27;
    - an OpenAPI description/disclaimer (m31);
    - an audit page verify-on-load (m32);
    - an AWS PHI note (m30);
    - "fraud pipeline" wording in the Lambda README (m29).
    - About *1 day* in total. [RL]

## How to run what I ran

- **Servers (still running in the background):**
  - API at http://127.0.0.1:8000 (uvicorn PID 628713; wrapper PID in `logs/api.pid`; log `logs/api.log`).
  - Vite at http://127.0.0.1:5173 (node PID 595070; log `logs/web.log`).
  - The review database is SQLite `/workspace/claimshield-review/claimshield_review.db`, seeded with tiny seed 7 plus one investigator decision.
- **Restart:** `scripts/stop_servers.sh`, then `scripts/start_api.sh && scripts/start_web.sh`. For a fresh DB, delete `claimshield_review.db` first, then run `cd backend && uv run --no-sync python /workspace/claimshield-review/scripts/seed_demo.py`.
- **Screenshots:** `/workspace/claimshield-review/.venv-pw/bin/python scripts/screens.py` and `scripts/screens_extra.py`.
