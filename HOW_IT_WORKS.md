# How ClaimShield Nexus actually works

This is the from-scratch explainer for Team SE7EN.  
`JUDGING.md` is how to present. This file is how to **understand**.

If you only remember one chain:

> Claims are billed → detectors raise **alerts** → we bundle related alerts into a **case** → we **rank** cases into today’s SIU desk → an investigator **opens the case**, sees **where every result came from**, and a **human** records the next step.

The model never names a provider “fraud.” An alert is a suspicion to verify.

---

## 0. The world this software lives in

After a clinic, pharmacy, or home-health agency treats a Medicaid member, they send a **claim** (a bill). The payer **adjudicates** it (pays, denies, or adjusts). That already happened before we show up.

**ClaimShield sits after payment.** We look at the paid extract and ask: is there a pattern worth a special investigations unit (SIU) look?

Three different words people mix up:

| Word | Meaning |
| --- | --- |
| **Fraud** | Someone *knowingly* billed false claims or took kickbacks |
| **Waste / abuse** | Unnecessary or inflated billing, not always criminal |
| **Improper payment** | Paid wrong for any reason, often missing paperwork |

CMS’s big dollar figure (about 6% of Medicaid) is **improper payments**. Most of that is documentation. **Do not call it fraud.**

The SIU has a handful of investigators and a **45-day** screening clock. They cannot open 1,000 alerts. They can work a few dozen **cases**.

That is the whole product: turn noise into a short, explained desk.

---

## 1. Four objects you must not mix up

### Claim / claim line

A **claim** is the header: member, billing provider, dates, paid amount.  
A **claim line** is one service on that bill: code, units, minutes, rendering NPI, paid.

Our extract is CSVs (or a synthetic generator that writes the same CSVs): `member`, `provider`, `claim`, `claim_line`, plus extras like EVV visits, inpatient stays, ownership, referrals, exclusion list.

### Alert

One detector saying “this looks off” on one provider (usually), pointing at one or more line IDs.

Examples:

- Rule: date of service after date of death
- Anomaly: this DME supplier’s units sit far above similar DME suppliers
- Graph: these NPIs share an owner / TIN / contact, or one clinic soaks up almost all referrals

An alert is **not** a case and **not** a verdict.

### Case

The unit an investigator actually opens. Several alerts that belong together.

This is the decision you asked about, and mentors agreed:

> Instead of paging the investigator with every alert, **group related alerts into a case** and put that case on the **portal**.

### Queue (the desk)

The ranked list of cases for **today**, given investigator **hours** and a slot cap. Cases that do not fit stay **open on a tracked backlog**. They are not closed.

---

## 2. What you proposed, what mentors said, what we coded

### What you proposed

“We will not send every alert to the inspector. We will categorize by case. Similar stuff from similar providers just goes to the portal.”

The first half is right. The second half needed a fence.

### What mentors said (in substance)

- Grouping related alerts into cases is sensible. Review a **provider’s pattern** together.
- The **portal is the queue**. You do not need a notification per alert unless the problem statement requires one.
- Make a case easy to act on: which alerts and claims were grouped, **why** they belong together, supporting evidence, priority.
- **Be careful with “similar providers.”** Peers used for comparison must not automatically become part of the same investigation. Put two providers in one case only when you have a **specific, visible connection** or a **shared suspicious pattern**.
- The investigator must still open the case, inspect **individual alerts**, and record a decision.
- Urgent items must stay visible even when folded into a larger case.
- Wherever you show a result, show **where the data came from and how you got there**.

### What we implemented

**Same billing provider → one case.**  
If provider A has a duplicate-claim alert and an upcoding anomaly, that is one investigation, not two emails.

**A second NPI joins the case only for these links:**

- identity ring (shared owner / TIN / contact)
- excluded owner
- concentrated referral (referral monopoly)

**Anomaly “peer_ids” stay out.**  
Those IDs are “we compared you to these similar clinics.” They are a **baseline**, not co-suspects. The API calls them `comparison_peers_held_out`. You will see that phrase on the workspace.

**Harm-4 signals stay labeled** after grouping (after death, excluded party, excluded owner) so a big referral case cannot hide a death-bill.

That is the grouping engine. It lives in `backend/src/claimshield/cases/builder.py`. Provenance text is built in `backend/src/claimshield/cases/provenance.py`.

---

## 3. How an extract becomes the queue

Think of one **run**. A run is “we looked at this extract, right now, with this many investigator hours.”

```
1. Load extract
   Manager: POST /api/v1/batches  { profile: tiny, seed: 7 }
   or AWS: CSVs land in S3 incoming/ → Lambda → POST /api/v1/aws/ingest

2. Detectors fire
   Rules + peer anomaly + graph
   Output: a pile of alerts, each with line_ids and evidence JSON

3. Case builder
   Bundle alerts (section 2)
   Score harm, severity, members affected, flagged dollars, evidence strength

4. Rank
   Five factors: severity, exposure, member impact, evidence, urgency
   Harm ≥ 4 takes a reserved slice of hours first
   Weak evidence (< 0.40) → “gather evidence”
   Remaining hours: knapsack on the composite score
   Slot cap (default 20) = today’s recommended set
   Rest → tracked backlog (still open)

5. Portal
   Manager queue and investigator worklist show those cases
   Investigator opens one workspace and decides
```

**Tiny seed 7** is the canned demo extract. It plants known schemes so the queue is not empty. Ground-truth labels are **not** fed into detectors. They exist so we can check ourselves later.

---

## 4. The three detectors, in plain language

### Rules (hard catalog)

If-then checks on fields we already have. After death uses `member.date_of_death` vs line date of service. Excluded party matches the exclusion list to an NPI or owner name. These are the easiest to explain: “this field, this table, this policy cite.”

### Peer anomaly

“Is this provider weird **compared with clinics like them**?” Same specialty, type, rural flag. If they are an outlier, we raise an alert **on them**, and we **remember** who we compared against so we can show it. We do **not** open a case on the peers.

### Graph

People and places as nodes, relationships as edges: billed, rendered, owns, referral, shared TIN, shared location, shared contact. Rings and monopolies only show up here. This is also the **only** honest reason two NPIs share a case.

---

## 5. Ranking — why this case is on top

Mentors (and you) did not want “sort by money.” The composite is:

| Factor | Weight | Intuition |
| --- | --- | --- |
| Severity | 0.22 | How ugly is the scheme / harm level |
| Exposure | 0.22 | How many dollars are in the flagged lines (scaled vs other cases) |
| Member impact | 0.22 | Harm × members. Manager can turn a **member-weight** slider to care more about people than dollars |
| Evidence | 0.18 | How well supported the hit is |
| Urgency | 0.16 | 30/60/90-day hazard + how close the 45-day clock is |

**Harm ≥ 4** (after death, excluded party/owner) does not wait in the knapsack. It takes a reserved share of hours so member safety is not crowded out by a huge billing mill.

**Capacity** is the other half. If you have 40 hours and 15 slots, the model fills that backpack. It does not pretend the team can work 200 cases.

**Human loop:** Promote / Defer on the queue, with a written reason. Decide on the workspace: request more information, refer deeper, watch, or dismiss. Reason must be long enough to be real (≥ 20 characters). Optional “ladder” (education letter, records, prepayment, MFCU, *recommend* payment suspension). **We never suspend payment.** That is the state’s 42 CFR 455.23 call.

---

## 6. Is the queue “dynamic”?

You asked this later. Here is the precise picture.

**Inside one run, order is ranked, not random.** Harm first, then composite. Factor bars on the page use **today’s** date for the 45-day clock.

**The set of cases is a snapshot of that run.** New CSVs or a new synthetic load create a **new run**. **Recompute queue** re-detects the **same extract** with new hours / member weight / slots. It is for “the desk changed,” not “a claim arrived this second.”

**Lanes do not reshuffle while someone is writing a brief.** That is on purpose. Due process and a stable evidence pack beat a live ticker.

If a lot of fraud starts overnight:

1. That extract is loaded or ingested.
2. A new run packs the desk.
3. Harm-4 still goes to the top.
4. Extra cases stay **visible** on tracked backlog.
5. A manager can promote.

We did **not** build a streaming queue. That was a product choice, not a missing button.

---

## 7. Evidence: “where did this come from?”

You asked that every result show **the data source and the path**. That is now on the case payload as `grouping` + `provenance`, and in the UI.

**Path we show (six steps):**

1. **Extract** — which batch / generator / S3 prefix  
2. **Rules** — how many catalog hits  
3. **Peer anomaly** — how many peer alerts; peers are a baseline  
4. **Network** — how many graph alerts  
5. **Case builder** — the grouping sentence (same provider vs visible link)  
6. **Rank** — why this case sits where it sits  

**Per alert (findings + evidence drawer):**

- detector method (rule vs peer vs graph)
- tables used and what each table is for (`claim`, `claim_line`, `member`, `exclusion_record`, …)
- fields that were in the evidence (code, dates, z-score, owner_id, …)
- supporting claim line IDs
- comparison peers held out, if any

**Per claim line:**

- `source_system` (for the demo: `generator`) and received date so you can say “this row came from the extract, not from a mystery model.”

Nothing here is a courtroom exhibit generator. It is so an investigator (and a judge) can walk backward from a badge to a table.

---

## 8. Where to *see* each idea in the app

Start backend `:8000`, frontend `:5173`.  
Login `manager@demo.claimshield` / `demo-manager`. Load **tiny seed 7**.

| Idea | Where |
| --- | --- |
| Alerts grouped, not paged | Queue case cell: `2 grouped alerts · 2 linked NPIs · urgent still visible` |
| Why they were grouped | Hover that line, or workspace **Overview** → “Which alerts sit in this case” |
| Peers not in the case | Overview grouping text; findings lineage “comparison peers held out” |
| Urgent still visible | Pink chip on the workspace header; harm badge on the queue |
| Evidence trail | Overview bottom: Extract → … → Rank, plus source tables |
| Per-finding origin | **Findings** → “Where this result came from”; click card → **drawer** |
| Claim origin | **Claims** → **Source** column |
| Human decision | **Decide** tab; queue Promote/Defer |
| Capacity ranking | Queue factor bars; member-weight and hours sliders; **Recompute queue** |
| Network connection | **Network** tab (two hops). That graph is exploration. Case membership is still only the link kinds above. |
| Investigator desk | `/investigator/cases` — same grouping line, take ownership |

A good walkthrough case after seed 7 is a **harm-4** row with **linked NPIs** (after-death + referral is the story: two real links, not “similar DME suppliers”).

---

## 9. AWS, without the mythology

There is already an S3 bucket and a Lambda named `claimshield-s3-processor`. We did **not** rebuild those.

```
incoming/*.csv
    → Lambda (thin: “a file appeared”)
    → POST /api/v1/aws/ingest  with X-ClaimShield-Internal-Token
    → same persist + execute_run as a local batch
    → same UI
```

Lambda is **not** the fraud engine.  
`http://127.0.0.1:8000` cannot be Lambda’s API URL. Live ingest needs a public HTTPS FastAPI. Local demo uses **Load batch** and ignores AWS.

---

## 10. What each major file is doing

| Place | Job |
| --- | --- |
| `backend/src/claimshield/rules/engine.py` | Catalog alerts |
| `backend/src/claimshield/anomaly/` | Peer outliers |
| `backend/src/claimshield/graph/` | Network alerts |
| `backend/src/claimshield/cases/builder.py` | Alerts → cases (grouping rules) |
| `backend/src/claimshield/cases/provenance.py` | Lineage sentences and source tables |
| `backend/src/claimshield/queue/rank.py` | Five factors + composite |
| `backend/src/claimshield/pipeline/service.py` | One run: detect, knapsack, persist |
| `backend/src/claimshield/api/routers/batches.py` | Load + queue JSON (`alert_group`) |
| `backend/src/claimshield/api/routers/aws.py` | Machine ingest |
| `frontend/src/features/queue/ManagerQueuePage.tsx` | Desk |
| `frontend/src/features/workspace/*` | Case, lineage, decide |
| `JUDGING.md` | Pitch and Q&A |

---

## 11. The decisions we already froze

These were product choices, not leftovers:

1. **Case = grouped alerts**, portal = queue.  
2. **Peers are for scoring**, not for joining the investigation.  
3. **Show provenance** on every result surface.  
4. **Recommend only.** Flag ≠ fraud.  
5. **Harm first + capacity knapsack + named backlog.**  
6. **Queue refreshes on a run**, not as a live stream.  
7. **This is the hackathon build.** No extra screens, no extra model, no live shuffle unless the problem statement forces it.

If you can explain sections 1, 2, 5, 6, and 7 out loud, you understand the project.
