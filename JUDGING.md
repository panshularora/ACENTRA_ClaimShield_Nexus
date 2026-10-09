# ClaimShield Nexus — judging and presentation brief

**Team:** SE7EN  
**Event:** BUILD TO CARE 2026 · Acentra Health · Problem Statement 3 (Hard)  
**Product:** ClaimShield Nexus — post-adjudication SIU desk for Medicaid-like fraud, waste, and abuse (FWA)

Read this before you present. It matches what the code actually does. Do not claim more than this file says.

---

## 1. In 30 seconds

Medicaid SIU teams get thousands of unexplained claim **alerts** and only enough hours to work a few dozen **cases**. ClaimShield Nexus turns those alerts into ranked, evidence-backed cases that fit investigator capacity.

A human records every next step. The model **recommends**. It never prints **fraud** on a provider.

**One sentence:** we collapse alerts into cases, show why they were grouped and where the data came from, put harm first, pack the rest into today’s hours, and keep everything else on a tracked backlog.

---

## 2. The problem we are solving

### Who is hurting

- **SIU / program-integrity investigators** drown in unconnected alerts.
- **Honest providers** get disrupted by weak or unexplained flags.
- **Members** are at risk when after-death billing, excluded parties, or dangerous overlap is buried under noise.
- **The program** loses money on schemes nobody has hours to open (rings, shared owners, concentrated referrals).

### Why it is hard

- Fraud, waste, and abuse are different. An **improper payment is not fraud**. CMS FY2025 Medicaid improper payments: **6.12% / $37.39B**, and most of that is documentation, not proven fraud.
- Patterns live **across claims**: same owner, same TIN, same contact, referral monopoly, peer outlier. One claim line is not the story.
- Investigator **time** is the scarce resource. Ranking by dollars alone opens the wrong work and misses member harm.
- Federal process: screen a lead, investigate, document, due process (**42 CFR 455.13–455.16**). CMS-style screening clock is **45 days**. **42 CFR 455.23** payment suspension is a **state** decision. We only **recommend**.

### What Acentra cares about

Acentra already sells ClaimsSure, Audit Studio, RuleIT, Navigator, eCAMS. We sit **downstream of claims adjudication** and **feed program integrity**: explainable leads, evidence packs, assignment, disposition, audit, precedent. We speak their language, we do not pretend to replace eCAMS.

---

## 3. What we built (the product)

A working SIU application, not a slide deck:

| Surface | Who | What they do |
| --- | --- | --- |
| Landing `/` | Anyone | 3D story: improper payment ≠ fraud, cases are networks, harm goes first |
| Login `/login` | All roles | Live cookie JWT, RBAC |
| Manager queue `/manager/queue` | Manager | Load extract, set hours / member weight / slots, see ranked desk, promote/defer |
| Investigator worklist `/investigator/cases` | Investigator | Take ownership of today’s recommended cases |
| Workspace `/investigator/workspace/:id` | Investigator | Overview, findings, brief, claims, timeline, network, decide |
| Precedents `/wiki/proposals` | Analyst / manager | Human-approved wiki pages from closed work |
| Audit `/audit` | Auditor | Hash-chained append-only log |

**Live demo:** [https://claimshield-nexus-api.onrender.com/login](https://claimshield-nexus-api.onrender.com/login)  
(Free Render can sleep; first hit after idle may take ~30s.)

**Demo logins** (password matches `demo-<role>`):

| Email | Role |
| --- | --- |
| `manager@demo.claimshield` | Manager — load batch, queue |
| `investigator@demo.claimshield` | Investigator — take case, inspect, decide |
| `analyst@demo.claimshield` | Analyst — wiki, no case read |
| `auditor@demo.claimshield` | Auditor — audit log |

---

## 4. How data becomes a case (the pipeline)

This is the spine. Draw it if you have a whiteboard.

```
Extract (synthetic generator or S3 CSVs)
        │
        ▼
   Rules engine     → hard catalog hits on claim lines
   Peer anomaly     → like-with-like specialty / type / rural outliers
   Network graph    → owner, TIN, contact, referral links
        │
        ▼
   Case builder     → alerts for one NPI share a case;
                      extra NPIs join only on a visible link
        │
        ▼
   Rank + knapsack  → harm 4 first; rest packed into hours/slots
        │
        ▼
   Portal queue     → investigator opens the case, inspects evidence, decides
```

**Ground-truth labels are never features.** They exist so we can evaluate. The model does not “know” which rows were planted.

**No AMA CPT.** Codes are synthetic / HCPCS II / NDC-style. Synthetic NPIs pass Luhn.

### Layer 1 — Rules

Deterministic catalog on claim lines. Examples: duplicate, after death, excluded party, daily minutes cap, inpatient overlap, unit cap, NCCI-style PTP. A hit is a **suspicion to verify**, with a policy cite.

### Layer 2 — Peer anomaly

Compare this provider to **similar** providers (specialty, type, rural). Robust z / IQR-style fences. Those similar providers are a **baseline**. They are **not** co-subjects of the case.

### Layer 3 — Graph

Provider–member–owner–location–referral graph. Alerts for identity rings, excluded owners, concentrated referral. This is how two NPIs can honestly sit in one investigation: a **visible connection**.

### Layer 4 — Case builder (mentor-aligned)

- All alerts for **one billing provider** → one case (the portal, not a pager per alert).
- Merge NPIs only for `identity_ring`, `excluded_owner`, or `referral_monopoly`.
- Comparison peers stay **held out**.
- Urgent harm (after-death / excluded party / excluded owner) stays **visible** after grouping.

### Layer 5 — Rank the desk

Each case gets five factors (weights in parentheses):

| Factor | What it means |
| --- | --- |
| Severity (0.22) | Scheme / harm level |
| Exposure (0.22) | Flagged dollars, scaled against peers |
| Member impact (0.22) | Harm × members affected (slider can raise this) |
| Evidence (0.18) | How well the hit is supported |
| Urgency (0.16) | Horizon risk (F30/F60/F90) + 45-day clock |

Then:

1. **Harm ≥ 4** takes a reserved slice of investigator hours (`harm_priority`).
2. Weak evidence (< 0.40) → **gather evidence**, not dismiss.
3. Remaining hours packed by **knapsack on the composite score**.
4. Slot cap (default 20) trims today’s recommended set.
5. Everything else stays **open on tracked backlog**. Not a dismissal.
6. Manager can **Promote / Defer** with a reason (human loop).

**The queue is ranked, not live-streaming.** A new extract (load batch or S3) or **Recompute queue** builds a new run. Opening the page refreshes factor bars and the 45-day clock. Lanes stay still while someone is working a case. If a surge of fraud arrives, it lands on the **next run**: harm first, leftover named on backlog, human can promote.

---

## 5. How the investigator works a case

Open a case from the queue (example after tiny seed 7: harm-4 grouped case such as **Anthony Mcgee / `CASE-EI04MB32YY`** — after-death + concentrated referral, two NPIs).

| Tab | Show this |
| --- | --- |
| **Overview** | Why it ranked here (factor bars). Which alerts sit in this case and why. Case NPIs. Evidence trail: Extract → Rules → Peer anomaly → Network → Case builder → Rank. Source tables. Urgent chip if harm-4 is inside the group. |
| **Findings** | Each detector card: rule/graph/anomaly, policy, supporting lines, **where the result came from**. |
| **Brief** | Cited investigation brief (template; LLM optional, validator drops uncited sentences). Same evidence trail underneath. |
| **Claims** | Line table. **Source** column = extract origin (e.g. `generator`) and received date. Click a line. |
| **Timeline** | Events on the member/provider over time. |
| **Network** | Two-hop neighbourhood (billed, rendered, owns, referral, shared TIN/location). Comparison peers are not parties. |
| **Decide** | Human only: request more information, refer deeper, keep under watch, or dismiss with reason (≥ 20 characters). Optional action ladder (education letter, records, prepayment, MFCU, **recommend** 455.23). Attaches the alerts you inspected. |

Member names stay **masked** unless a permitted role reveals them; unmask is audited (minimum necessary).

A decision can propose a **precedent wiki** page. A human approves it. The audit log is **hash-chained**.

---

## 6. How data gets in

**Local demo (what you will show):** manager clicks load **tiny / seed 7**. `POST /api/v1/batches`. Synthetic generator writes the extract. Pipeline runs. Queue fills.

**Optional AWS path (same engine):**

```
S3 incoming/*.csv
  → existing Lambda claimshield-s3-processor
  → POST /api/v1/aws/ingest  (shared internal token)
  → persist_dataset + execute_run
  → same queue and workspace
```

Lambda does **not** score fraud. Detection stays in FastAPI. Live S3 needs a **public HTTPS API**. `localhost` cannot be Lambda’s URL. Local demo does not need AWS.

---

## 7. Stack (if they ask “what did you use”)

- **Backend:** Python, FastAPI, SQLAlchemy (SQLite local / Postgres in Docker)
- **Auth:** cookie JWT, Argon2id, RBAC, CSRF
- **Graph:** NetworkX (no Neo4j, no GNN)
- **Queue:** multi-factor rank + harm-reserved knapsack
- **Frontend:** React, Vite; Three.js on landing/login only; SIU screens are a paper/navy workstation
- **Audit:** append-only hash chain
- **Data:** our generator (schemes S01–S21, rings G1–G3, camouflage C1, hard negatives). S06 ambulance held out of “model training” language; still visible to rules.

We did **not** build Kafka, Kubernetes, ECS, or Neo4j. That is intentional: one pipeline, explainable, demoable on a laptop.

---

## 8. What we will never say on stage

- “The AI found fraud.”
- “This provider is guilty.”
- “Improper payment rate = fraud rate.”
- “Similar providers are in the same case.”
- “The queue live-shuffles every new alert.”
- “We suspend payment.” (State decides 455.23.)
- “We use CPT.”

Correct lines:

- “Ranked suspicion for human review.”
- “Grouped alerts, held-out comparison peers.”
- “Harm first, then capacity, backlog still open.”
- “Here is the table, the rule, and the graph link.”

---

## 9. 90-second demo script

**Prep:** open [https://claimshield-nexus-api.onrender.com](https://claimshield-nexus-api.onrender.com) (or local backend `:8000` + frontend `:5173`). Manager login already filled.

1. **Landing (10s).** Scroll: “Improper payments are not fraud. Cases are networks. Harm goes first.” Click **Enter SIU**.
2. **Sign in (5s).** `manager@demo.claimshield` / `demo-manager`.
3. **Load (15s).** Tiny profile, seed 7, ~40 hours. Point at lane hours: harm priority, selected, needs evidence, monitor/backlog.
4. **Queue (20s).** A harm-4 row: “N grouped alerts · linked NPIs · urgent still visible.” Hover for why they belong together. Factor bars: not dollars alone. “If we cannot work it today it stays on tracked backlog.”
5. **Workspace (30s).** Open investigation. Overview: grouping sentence, alert chips, evidence trail, source tables. Findings: “where this result came from.” Optional: Claims **Source** column, Network two-hop.
6. **Decide (10s).** Investigator (or manager with decide): take ownership if needed, write a 20+ character reason, pick a next step. “A person just recorded this. The model did not close it.”

If time: **Recompute** with higher member-impact weight and show the desk change. Or **Audit** after unmask/decide.

**Hero case to memorize:** after-death + concentrated referral, two NPIs, harm 4, grouped alerts on the portal.

---

## 10. Likely judge questions (answer these)

**Why not send every alert to the investigator?**  
Mentors agreed: group related alerts into cases. The portal is the queue. Per-alert noise burns hours.

**Why aren’t similar providers in the same case?**  
Peers are a scoring baseline. We merge NPIs only on a visible link (ring, excluded owner, referral). Otherwise we smear honest neighbors.

**Is the queue dynamic if fraud suddenly spikes?**  
Ranking is dynamic **inside a run**. New claims enter on the **next run** (load, ingest, or recompute). Harm-4 still goes first. Overflow stays named. A manager can promote. We do not reshuffle the table while someone is writing a brief.

**How do we know where a number came from?**  
Overview evidence trail, findings lineage (tables + roles + method), claims source column, evidence drawer. Ground truth is labels only.

**What if evidence is weak?**  
Lane `needs_evidence`. Recommend records / EVV, not dismissal and not a fraud label.

**Can the investigator still see one alert?**  
Yes. Open the case, inspect each finding, attach those you reviewed, record a decision.

**What about due process?**  
Recommend only. Masked members. Unmask logged. Hash-chained audit. 45-day clock on the row. Payment suspension is a state call.

**Did you train a big model?**  
Rules + peer stats + graph + a simple discrete hazard for 30/60/90. Explainable on purpose. CMS-style factors beat a black box in this setting.

**Where does this sit vs Acentra?**  
After adjudication, into SIU. Complements ClaimsSure / Audit Studio / RuleIT: explainable case, evidence pack, assignment, disposition, precedent.

**What would you build next (if they bite)?**  
Refresh the desk on each new extract / a schedule. Keep lanes stable during an open investigation. Do not add a live ticker.

---

## 11. Roles on stage (split the talking)

| Person | Owns |
| --- | --- |
| Opening | Problem, improper payment ≠ fraud, SIU hours |
| Product | Queue, grouping, harm-first knapsack, HITL |
| Investigator path | Workspace, lineage, decide |
| Integrity | 42 CFR, 45-day clock, audit, masking, recommend-only |
| Close | “N alerts → M cases that fit today; the rest stay tracked.” |

---

## 12. Run it locally (if the demo machine is cold)

```bash
# terminal 1
cd backend
uv sync --extra dev
# .env from .env.example; leave CLAIMSHIELD_INTERNAL_TOKEN empty
unset PYTHONPATH
.venv/bin/uvicorn claimshield.api.main:app --reload --app-dir src --host 127.0.0.1 --port 8000

# terminal 2
cd frontend
npm install
npm run dev
```

Open http://127.0.0.1:5173 → Enter SIU → manager login → load tiny seed 7.

Health check: http://127.0.0.1:8000/healthz

---

## 13. One slide if you only get one

**ClaimShield Nexus**  
Alerts → cases → ranked SIU desk → human decision  

- Group by provider / visible link; comparison peers held out  
- Harm first, then severity · exposure · members · evidence · urgency inside hours  
- Every result shows its extract tables and detector path  
- Overflow is tracked, not dropped  
- Recommend only. Improper payment ≠ fraud.
