# ClaimShield Nexus: domain and factual accuracy audit (read-only)

- **Repo:** https://github.com/panshularora/ACENTRA_ClaimShield_Nexus, `main` @ `a9679fa`. Cloned to `/workspace/claimshield-domain-audit/repo`; nothing was modified, committed or pushed.
- **Audited:** 8 Oct 2026 (IST).
- **Source of truth:** `/workspace/acentra-ps3/01_PS3_research_brief.md` (cited below as "brief §n"), plus `/workspace/factcheck/` and the plan in `/workspace/claimshield/docs/`.
- **How claims were checked:**
  - Every line reference below was re-checked in the `a9679fa` clone.
  - "Observed in run" means `/workspace/claimshield-review/logs/case_packs.json` and `batch_load.json`: the tiny seed-7 run on the other agent's checkout, which I read but did not modify.
  - Anything I could not verify is marked **[UNVERIFIED]**.
- **Target audience:** Acentra payer-integrity judges, who will read the landing page, the manager queue, the case workspace and brief, and the README.

---

## 0. Executive summary: the five things a payer-integrity judge will catch first

1. **The probability and hazard numbers are invented.**
   - `P(confirm)` is a hand-set logistic (`builder.py:230-245`).
   - "F30/F60/F90 discrete-time hazard" is a made-up constant monthly rate (`service.py:27-36`).
   - Both are shown as percentages and as "survival" or "still-burning chance" on the landing page, the queue, the workspace, the drawer and the brief.
   - The README says a model is trained ("held out of model training"), but no model is trained and no LLM exists.
   - The team's own plan says to hide F30/60/90 and label the score "uncalibrated" when no model exists (plan L943).
2. **"Harm 4 / member safety" is assigned to the wrong things.**
   - Harm 4 = service after death, an LEIE NPI hit, or an owner-name LEIE hit (`builder.py:38`). None of these is a life-threatening risk to a living member, which is what the CMS harm scale means.
   - In the run, the three "harm-priority (member safety)" cases are exactly these three alert kinds. One of them is an LEIE "match" where the NPI matches but the name does not (see M4).
3. **Escalation goes straight to MFCU referral and payment suspension, and no manager approves it.**
   - `escalate` defaults to `mfcu_referral` (`workspace.py:52`, `DecisionBar.tsx:62`).
   - Investigators can pick "Recommend 42 CFR 455.23 payment suspension" (`DecisionBar.tsx:55`).
   - Decisions save `approved_by=None` (`workspace.py:1018`).
   - Under 42 CFR 438.608 an MCO/SIU refers to the **state Medicaid agency**, not the MFCU. Suspension needs a state credible-allegation determination.
   - The plan (L1141, L49) promised the opposite.
4. **Several detectors would fire on normal billing.**
   - "Clone billing" flags identical **paid amounts**. Medicaid FFS pays from a fee schedule, so identical paid amounts are the norm.
   - "Overlapping ambulance trips same vehicle-day" fires on any ambulance provider-day with 2+ lines and 90+ minutes, but a single transport is a base-rate line plus a mileage line.
   - "Doctor shopping", a member behaviour, is pinned on the member's first prescriber.
   - The sex-procedure rule ignores CMS's KX modifier and condition code 45 bypass, which makes it a bias risk for transgender and intersex members.
5. **Documents misstate facts.**
   - The Medicaid MUE file has **no MAI column**, but PAPERS.md and both plans use "MAI 3".
   - NCCI has no duplicate edit and no demographic or sex edit, but `rules.yaml` and PAPERS.md tag those rules NCCI.
   - The repo's copy of the research brief says ClaimsSure and Audit Studio help **Utah**. The corrected brief says the blog says they were deployed in *other* states.
   - "Synthetic NPIs pass Luhn" is mis-described (see M17).
   - eCAMS integration is stated as fact.
   - The UI is branded "Acentra Health SIU".

Fix those five and the product reads as credible. The ethical framing ("potential FWA pattern requiring investigation", "state decides", "improper payments ≠ fraud") is already strong (§3).

---

## 1. MUST FIX before judges

Each item gives **Where** (file:line), **Current**, **Problem**, **Replace with**, and **Source**.

### M1. P(confirm) and F30/60/90 are uncalibrated heuristics presented as model probabilities and as a hazard or survival curve

**Where (logic):**
- `backend/src/claimshield/cases/builder.py:230-245`: `z = -2.0 + 2.4*evidence + 0.35*min(3,n_detectors)`, then `+0.4` if harm≥4, `+0.25` if graph, `+0.5` if prior, then a sigmoid. These are hand-picked constants with no training and no calibration.
- `backend/src/claimshield/pipeline/service.py:27-36`: `monthly = 0.05 + 0.28*p_confirm + 0.03*harm`, clamped to 0.02–0.65, then `F(k)=1-(1-m)^k`.
  - This just re-expresses P(confirm) and harm. It is not a fitted hazard.
  - The event it is the "probability" of is never defined.

**Where (claims shown to users):**
- `frontend/src/features/landing/LandingPage.tsx:70`: "Each case carries a discrete-time hazard: probability the pattern is still burning at 30, 60, and 90 days."
- `LandingPage.tsx:72`: "F30 / F60 / F90 are survival of the pattern, not a guilt score."
- `LandingPage.tsx:77-79`: "Still-burning chance at one month" / "Two-month discrete hazard".
- `frontend/src/features/queue/ManagerQueuePage.tsx:602`, `:623` (P(confirm)); `:624`, `:335` ("Risk column uses F{h}").
- `frontend/src/features/workspace/WorkspacePage.tsx:200` (P(confirm)), `:268` (F30 / F60 / F90).
- `frontend/src/components/CaseDrawer.tsx:62`, `:70`.
- `frontend/src/lib/format.ts:85`: "Selected: P(confirm) …".
- `backend/src/claimshield/cases/workspace.py:615-618`: the brief prints "P(confirm) 89%; … 30/60/90 risk 0.749 / …".
- Observed in run: the brief has `"confidence": 0.894`.

**Problems:**
- (a) Showing "P(confirm) 89%" implies an estimated probability that a case will be substantiated. None was estimated.
- (b) `1-(1-m)^k` is a CDF (the probability that an event *has occurred* by month k), not survival. "Survival of the pattern" and "still burning" are the complement and are mathematically wrong.
- (c) The brief (§6) asks for a discrete-time hazard model calibrated with a reliability plot and backtested on rolling-origin splits.
- (d) The plan itself (CLAIMSHIELD_NEXUS_PLAN.md L943) says: "Fusion falls back to transparent weighted score labelled 'uncalibrated'; F30/60/90 hidden, not guessed".

**Replace with:**
- Option A (quick, honest): rename P(confirm) to **"Priority score (0–1, heuristic, uncalibrated)"**. Hide F30/F60/F90, or label them **"Illustrative escalation index (rule-of-thumb, not a model)"**.
- Landing L70 → "Each case carries a transparent priority score built from evidence strength, number of independent detectors and harm. It is a heuristic, not a calibrated probability; a trained hazard model is future work once investigation outcomes exist."
- Delete L72 and L77-79, or replace them with "F30/F60/F90: placeholder for a future calibrated hazard model (not shown in this build)."
- Brief `workspace.py:615` → "Priority score 0.89 (heuristic, uncalibrated)."
- Option B: actually fit the logistic and hazard on the synthetic `investigation` labels, then show calibration and the model version. Even then, label it "calibrated on synthetic data only".

**Source:** brief §6 (hazard, calibration, rolling-origin backtest); plan L46, L943; NIST AI RMF (valid and reliable; transparent): https://nvlpubs.nist.gov/nistpubs/ai/NIST.AI.100-1.pdf

### M2. "AI / the model recommends today's queue" is an overclaim, and there is no model in the loop

**Where:**
- `backend/src/claimshield/queue/rank.py:30-31`: "The model recommends today's queue from combined factors…" This is stored in every run (`batch_load.json` ranking_policy.note).
- `LandingPage.tsx:55`: "AI recommends today's 20."
- `ManagerQueuePage.tsx:503`: "AI recommends a top-N desk…"
- `README.md:69` and `backend/README.md:41`: "S06 ambulance is held out of model training (still visible to rules)."

**Problems:**
- The ranking is a fixed weighted sum (0.22/0.22/0.22/0.18/0.16) plus a 0/1 knapsack on hours. That is a transparent policy, which is good, but it is not AI or a trained model.
- No model is trained anywhere. `lightgbm` and `shap` are listed in `pyproject.toml` but never imported, and `config.py:34-36` has LLM settings with no LLM path. "Held out of model training" is therefore false.
- A judge who asks "show me the model" will find nothing.

**Replace with:**
- rank.py note → "A transparent, rule-weighted policy recommends today's queue from five factors inside investigator capacity. Weights are fixed and shown. Investigators decide what to work. Cases outside today's slots stay open on a tracked backlog."
- Landing L55 → "The ranking policy proposes today's top 20; investigators decide."
- README L69 → "S06 (ambulance) is a held-out scheme type reserved for a future ML evaluation; in this build only rules see it."
- Remove the unused `lightgbm` and `shap` dependencies, or add a comment saying they are reserved.

**Source:** brief §5.3 and §6; GAO-26-107799 (analytics produce leads, not determinations): https://www.gao.gov/products/gao-26-107799

### M3. The harm scale is misapplied: "Harm ≥ 4 (member safety)" is given to after-death, LEIE and owner-name hits

**Where:**
- `backend/src/claimshield/cases/builder.py:38`: `HARM4_KINDS = {"after_death","excluded_party","excluded_owner"}`; `:39`: HARM3 = inpatient_overlap, doctor_shopping, daily_minutes_cap.
- `ManagerQueuePage.tsx:507`: "Harm ≥ 4 is taken first (member safety)".
- `LandingPage.tsx:57`: "Harm-priority cases jump the dollar queue. Vulnerable members come first."
- `backend/src/claimshield/queue/explain.py:25-26`: "Harm {h} is at the CMS-style override. Beneficiary harm takes a reserved slice…"
- `pipeline/service.py:47-50`: every harm≥4 case goes to the harm-priority lane.
- Observed in run: the harm-priority lane holds (1) an after-death plus 5-signal case, (2) "Austin Howard", an `excluded_party`-only case with an NPI match and a **name mismatch** (M4), and (3) "Thomas and Sons" (excluded_owner + ring).

**Problems:**
- The CMS PIM prioritisation scale treats the top level as patient harm (life-threatening or serious risk to beneficiaries).
- A claim for a member who has already died cannot harm that member. It is a financial and identity-misuse signal.
- An excluded provider is a serious *program* violation (CMPs, and payment is prohibited), but it is not automatically a member-safety risk.
- Meanwhile the alerts that *are* member-safety signals (opioid MME ≥ 120 across 4+ prescribers and 4+ pharmacies; services during an inpatient stay; more than 16 hours a day of therapy) sit at harm 3. In the run, "Christopher Dominguez" (daily_minutes_cap + inpatient_overlap, evidence 0.899) is in the backlog.
- Judges will see the "member safety" label applied to a deceased member's claim.

**Replace with:**
- Split into two axes: **program-integrity priority** (exclusion and after-death, an immediate-action lane) and **beneficiary-harm** (opioid patterns, inpatient overlap, impossible hours, unsafe-provider signals).
- Rename the lane "**Priority override (program integrity / potential beneficiary harm)**".
- Change `ManagerQueuePage.tsx:507` to "Priority-override cases are taken first (excluded provider, services after death, potential beneficiary harm)".
- Change `LandingPage.tsx:57` to "Priority-override cases (potential beneficiary harm, excluded providers) are taken before dollar-ranked work."
- Move doctor_shopping and inpatient_overlap to beneficiary-harm 4 if the team wants "member safety" to stay true.

**Source:** CMS Program Integrity Manual ch. 4 (prioritisation, patient harm): https://www.cms.gov/Regulations-and-Guidance/Guidance/Manuals/Downloads/pim83c04.pdf; brief §2 and §7. The exact wording of the 1–4 scale comes from the brief/factcheck notes. **[Re-check the scale wording against pim83c04 before quoting it on a slide.]**

### M4. LEIE matching is naive (NPI-only or name-only, no date check), and the seed data contains a false match that the product treats as harm 4

**Where:**
- `backend/src/claimshield/rules/engine.py:286-314` (`_excluded`): flags a provider if `npi_syn` is in the exclusion NPIs. It matches the **billing provider only**, does not compare names, and never checks that the date of service is on or after the exclusion date (or before any reinstatement).
- `backend/src/claimshield/graph/detect.py:127-167` (`_excluded_owner`): exact lowercase "first last" name match only, with no DOB, address or NPI.
- `data/reference/rules.yaml:87-91`: `G-OWN-001` "Owner name matches synthetic LEIE record", severity 4.
- `backend/src/claimshield/cases/workspace.py:118`: the evidence gap asks for "LEIE match packet (NPI, name, exclusion type and effective date)". This is good, but the detector does not use those fields.
- Seed data (`data/generated/tiny/`): exclusion NPI `2869189395` belongs to provider "Austin Howard", but the exclusion record's name is "Lauren Long". The product still opens a harm-4 case on it (observed in run: p 0.625, F90 0.749). Every exclusion DOB is `1965-03-12`.

**Problems:**
- Only about 8.9k of the roughly 84k LEIE rows carry an NPI (brief §4).
- OIG tells users to confirm a match with the online search, using name plus DOB, address or SSN/EIN.
- Payment is barred only for items and services furnished on or after the exclusion effective date.
- A name-only owner match at severity 4 is exactly the false-positive pattern the brief warns about (common names).
- A judge will ask how a common name is ruled out.

**Replace with:**
- Add a match-confidence ladder:
  - *Confirmed*: NPI plus name plus DOB or address agree, and DOS ≥ excldate.
  - *Probable*: name plus DOB, or name plus address.
  - *Possible*: name only. This is evidence, not harm 4; show it as "possible LEIE name match — verify on OIG exclusions search".
- Require DOS ≥ exclusion date.
- Check rendering providers and owners or managing employees (42 CFR 455.104/455.436) as well as billing.
- Fix the seed so planted exclusions agree on name and NPI, and add a deliberate name-mismatch hard negative that must *not* reach harm 4.
- Rule title → "Owner name resembles a synthetic LEIE record (unconfirmed)".

**Source:** brief §4 (LEIE NPI coverage, matching guidance); OIG LEIE downloads: https://oig.hhs.gov/exclusions/leie-database-supplement-downloads/; 42 CFR 455.436: https://www.ecfr.gov/current/title-42/chapter-IV/subchapter-C/part-455/subpart-E/section-455.436

### M5. Escalation defaults to "Referral to state MFCU", suspension can be picked by the investigator, and there is no manager approval

**Where:**
- `backend/src/claimshield/cases/workspace.py:42-62`:
  - `DEFAULT_LADDER["escalate"] = "mfcu_referral"`.
  - Labels: "Referral to state MFCU" and "Recommend 42 CFR 455.23 payment suspension (state decides)".
- `frontend/src/features/workspace/DecisionBar.tsx:31`: "Send to a fuller investigation or MFCU screening path."
- `DecisionBar.tsx:49-50`, `:55` (`escalate: ["mfcu_referral","prepayment_review","payment_suspension_recommend"]`), `:62` (default `mfcu_referral`).
- `workspace.py:1018`: `approved_by=None`.
- `LandingPage.tsx:93`: "State SIU keeps payment-suspension authority".

**Problems:**
- (a) Under 42 CFR 438.608(a)(7)–(8), a managed-care plan's compliance program/SIU refers suspected fraud to the **State** (Medicaid agency / PI unit). The State then refers credible allegations to the MFCU (455.21, 455.23(d)). A one-click "Referral to state MFCU" from an SIU analyst skips the state.
- (b) A 455.23 suspension is a State Medicaid agency determination after a credible allegation of fraud, with good-cause exceptions. "State **SIU**" is the wrong body: SIUs sit in MCOs and contractors.
- (c) Offering suspension to an investigator on a heuristic-scored case contradicts the team's own plan:
  - L1141: "Never proposed by the system; shown only as a human option after a manager records a credible-allegation determination."
  - L49: "the manager approves".
- (d) GAO-26-107799 notes that CMS cannot deny a claim solely on data analytics. Judges will expect a human approval step before anything adverse.

**Replace with:**
- Ladder labels:
  - "Refer to State Medicaid agency PI unit (for MFCU consideration)"
  - "Recommend prepayment review (state/plan policy)"
  - Remove `payment_suspension_recommend` from the investigator UI, **or** show it only to the manager after a recorded "credible allegation of fraud determination (state)", together with a 455.23(e)/(f) good-cause warning.
- Default for `escalate` → `medical_records_request` or "Full investigation".
- Require `approved_by` (manager) for any escalate or referral decision before the case status changes.
- `LandingPage.tsx:93` → "The State Medicaid agency decides on 42 CFR 455.23 payment suspension."
- `DecisionBar.tsx:31` → "Open a full investigation; a manager approves any referral to the State."

**Source:** 42 CFR 438.608: https://www.ecfr.gov/current/title-42/chapter-IV/subchapter-C/part-438/subpart-H/section-438.608; 42 CFR 455.23: https://www.ecfr.gov/current/title-42/chapter-IV/subchapter-C/part-455/subpart-A/section-455.23; CMS Managed Care Fraud Referral Toolkit: https://www.cms.gov/files/document/managed-care-fraud-referral-toolkit.pdf; OIG MFCU: https://oig.hhs.gov/fraud/medicaid-fraud-control-units-mfcu/; plan L49, L1141.

### M6. The 455.23 good-cause data exists but is never surfaced

**Where:**
- The generator creates `provider.sole_community` (`backend/src/claimshield/synth/generator.py:232`; `db/models.py:116`).
- Nothing in the backend case/brief code or the frontend reads it.
- Observed in run: "Jennifer Watson" is `sole_community=True` and sits in the **selected** lane with an $18,000, one-member case.

**Problem:** Good-cause exceptions (for example, access to care where the provider is the sole community provider) are part of the suspension rule. The brief (§10.1) calls a good-cause badge a quick, high-value fix. The data is already there.

**Replace with:** Add a badge in the case header and the brief: "Access consideration: sole community provider. 42 CFR 455.23(e) good-cause exceptions may apply to any payment suspension (state decision)."

**Source:** 42 CFR 455.23(e)–(f) (link above); brief §10.1.

### M7. The "Clone billing" detector would fire on any fee-schedule practice

**Where:**
- `backend/src/claimshield/rules/engine.py:428-447`: groups by billing provider, DOS, code and **paid** amount; fires when there are 8+ members. Score 0.9.
- `data/reference/rules.yaml:62-66`: "Identical paid amount cloned across many members same day", `SIU-CLONE`.

**Problems:**
- Medicaid FFS pays practitioners from a state fee schedule, so every claim for the same code from the same provider on the same day normally pays the **same amount**.
- The rule only works because the generator jitters every legitimate line's charge (`synth/generator.py:375-378`), which is a generator artifact (the leakage risk in brief §6/§9).
- "Cloning" in program integrity normally means **cloned medical-record documentation** (copy-paste notes), which claims data cannot see.

**Replace with:**
- Rename to "**High same-day volume of an identical service across many members**" and base it on volume versus peers (units or members per day relative to the specialty), not on identical paid amounts.
- Or keep it explicitly as a synthetic-only demo rule labelled "demo rule; not valid on fee-schedule data".
- Move "possible cloned documentation" into the evidence-gap list ("request notes to check for cloned documentation").

**Source:** MACPAC on Medicaid physician fee schedules: https://www.macpac.gov/subtopic/provider-payment/

### M8. The "Overlapping ambulance trips same vehicle-day" logic does not test overlap and fires on normal transports

**Where:**
- `backend/src/claimshield/rules/engine.py:398-425`: fires when one **rendering provider** on one DOS has 2+ lines of A0425/A0427 whose `minutes` sum to 90 or more.
- `rules.yaml:57-60`: title "Overlapping ambulance trips same vehicle-day".
- `workspace.py:104`: "Overlapping ambulance trips".

**Problems:**
- A single ALS emergency transport is billed as A0427 (base rate) **plus** A0425 (mileage). That is 2 lines by design.
- An ambulance supplier runs many trips a day.
- There is no vehicle ID, crew or pickup/drop-off time, so nothing here tests overlap.
- An ambulance-industry judge would spot this immediately.

**Replace with:**
- Only claim overlap if trip start/end times and a vehicle/crew ID are synthesised: same vehicle, intervals that overlap, different members.
- Otherwise rename it "**Ambulance trip volume per crew-day above peers (synthetic)**" and pair base and mileage lines as one trip.

**Source:** HCPCS Level II A0425 = ground mileage per statute mile; A0427 = ALS1 emergency base rate (CMS HCPCS quarterly update: https://www.cms.gov/medicare/coding-billing/healthcare-common-procedure-system/quarterly-update); OIG OEI-09-12-00351 (ambulance questionable billing): https://oig.hhs.gov/oei/reports/oei-09-12-00351.pdf

### M9. "Doctor shopping" (a member behaviour) is attributed to a provider, and the case grouping merges unrelated schemes

**Where:**
- `backend/src/claimshield/rules/engine.py:317-341`: groups opioid fills (MME ≥ 120 on any single fill) by **member** and fires on 4+ prescribers and 4+ pharmacies. It then sets `entity_id = grp.iloc[0].prescriber_id` and `line_ids=[]`.
- `workspace.py:101` and `format.ts:55`: "Doctor shopping".
- Observed in run: the brief says "Doctor shopping (R-RX-001) on 0 claim line(s) for entity PRV-52P4GQD2DS". That entity is an orthopaedics organisation, merged into a DME supplier's after-death case. The resulting case has 6 unrelated signal families (after-death, doctor shopping, sex, POS, clone, referral).

**Problems:**
- Doctor shopping is a **member** pattern. The usual payer response is a lock-in or restriction programme and care coordination, not an SIU case against whichever prescriber happened to be first.
- The rule also ignores the time window (OIG used "high amounts" plus multiple prescribers and pharmacies over a period).
- "0 claim lines" in a brief looks broken.

**Replace with:**
- Make the entity the member (masked).
- Route it to a "member-level pattern → pharmacy lock-in / care-coordination review" lane, and attach prescribers and pharmacies only as context.
- Label it "**Multiple-prescriber / multiple-pharmacy opioid pattern (member-level)**".
- Do not let member-level alerts join provider cases through union-find. Cap grouping so a case has one primary scheme family plus linked evidence.

**Source:** OIG OEI-02-17-00250: https://www.oig.hhs.gov/oei/reports/oei-02-17-00250.pdf; MACPAC lock-in programmes: https://www.macpac.gov/wp-content/uploads/2019/08/Pharmacy-and-Provider-Lock-in-Programs-in-Medicaid-Fee-for-Service.pdf

### M10. The sex-implausible procedure rule ignores CMS's documented bypass and is a bias risk

**Where:**
- `backend/src/claimshield/rules/engine.py:345-349`: `code == "PROC-MALE-01" & sex == "F"`, with no modifier or condition-code check.
- `rules.yaml:47-51`: severity 3, `policy_ref: NCCI-DEM`.
- `workspace.py:102` and `format.ts:56`: "Sex-implausible procedure".

**Problems:**
- CMS instructs providers to use the **KX modifier** (professional) or **condition code 45** (institutional) so that gender/procedure conflict edits are bypassed for transgender and intersex patients.
- A conflict is a claims-processing edit, not evidence of FWA. Flagging it at severity 3 in an SIU tool is a fairness and civil-rights risk that a responsible-AI judge will raise.
- It is also not an NCCI edit (see M12).

**Replace with:**
- Skip lines carrying KX or condition code 45.
- Lower the severity to 1 ("data-quality / coding check").
- Retitle it "**Sex–procedure coding conflict (data-quality check; KX/CC45 excluded)**".
- Add it to a fairness note in the README.

**Source:** CMS Transmittal R1877CP, "Instructions Regarding Processing Claims Rejecting for Gender/Procedure Conflict": https://www.cms.gov/Regulations-and-Guidance/Guidance/Transmittals/downloads/R1877CP.pdf

### M11. The PTP evidence-gap text gets modifier indicator 0 backwards

**Where:** `backend/src/claimshield/cases/workspace.py:120`: "Medical records supporting a PTP exception (modifier indicator is 0 in the synthetic table)."

**Problem:**
- PTP modifier indicator **0** means no modifier is ever allowed to bypass the edit; **1** means a modifier is allowed; **9** means not applicable.
- Asking for records "supporting a PTP exception" when the indicator is 0 shows a misunderstanding of NCCI.

**Replace with:** "Indicator 0: the column-two code is not separately payable with the column-one code under any modifier. Request the claim images to confirm the pair was paid together and the amount to recover. (For indicator-1 pairs, request records supporting a distinct-procedural-service modifier.)"

**Source:** CMS Medicaid NCCI: https://www.cms.gov/medicare/coding-billing/ncci-medicaid; Medicaid NCCI edit files: https://www.cms.gov/medicare/coding-billing/ncci-medicaid/medicaid-ncci-edit-files

### M12. NCCI is misattributed (duplicate and sex/demographic rules tagged as NCCI)

**Where:**
- `data/reference/rules.yaml:6`: `R-DUP-001` `policy_ref: NCCI-SYN-DUP`.
- `rules.yaml:51`: `R-SEX-001` `policy_ref: NCCI-DEM`.
- `data/reference/PAPERS.md:40`: "S14 | Sex-implausible procedure | NCCI medically unlikely / demographic edits".

**Problems:**
- Medicaid NCCI has exactly two edit types: PTP and MUE.
- Duplicate-claim checks are a separate claims-processing edit (and Acentra's eCAMS/RuleIT page describes "duplicate detection" as its own capability).
- Sex/procedure and age conflicts come from code-editor logic (for example the OCE/MCE in Medicare), not NCCI. **[UNVERIFIED for Medicaid specifically; I did not fetch an OCE/MCE source]**.

**Replace with:**
- `R-DUP-001 policy_ref: CLAIMS-DUP (payer duplicate-claim edit; not NCCI)`.
- `R-SEX-001 policy_ref: CODE-EDITOR-SEX (see CMS R1877CP)`.
- PAPERS L40 → "Sex–procedure conflict edit (code-editor logic; KX / condition code 45 bypass per CMS R1877CP)".

**Source:** https://www.cms.gov/medicare/coding-billing/ncci-medicaid (two edit types; Medicaid MUEs are per line); R1877CP (above); eCAMS HCE: https://acentra.com/technologies/ecams-hce

### M13. "MAI" is used for the Medicaid MUE file, which has no MAI column

**Where:**
- `data/reference/PAPERS.md:26`: "S04 | Excess units / MUE | CMS MUE / MAI 3 same-day split".
- `CLAIMSHIELD_NEXUS_PLAN.md:707`: "(MAI 3 logic)".
- `CLAIMSHIELD_NEXUS_PLAN.md:733`: "MUE: code, value, MAI 1/2/3, rationale".
- `CLAIMSHIELD_NEXUS_PLAN.md:745`: "Its MAI is not recorded in the brief: read it from the file".
- Same text in `CLAIMSHIELD_PLAN_DRAFT.md:635`, `:661`, `:673`.

**Problems:**
- The Medicaid practitioner MUE file has columns HCPCS/CPT code, MUE value and MUE rationale. There is no MAI column.
- Medicaid MUEs are adjudicated **per claim line**. The code correctly uses per-line caps; the docs are what's wrong.
- MAI (1/2/3) is a Medicare concept.
- I verified this against the Oct-2026 Medicaid practitioner MUE file in `/workspace/factcheck/`. That file also confirms A0425 = 250 with rationale "Clinical: Medicare Data", which matches `synth/codes.py`.

**Replace with:**
- PAPERS L26 → "CMS Medicaid MUE (per-line; Medicaid files carry no MAI) — units split across lines same day as an evasion variant."
- Plan L733 → "MUE: code, value, rationale (Medicaid files have no MAI; MAI is Medicare-only)".
- Plan L745 → "MUE 250, rationale 'Clinical: Medicare Data' (Oct-2026 Medicaid practitioner file)".

**Source:** https://www.cms.gov/medicare/coding-billing/ncci-medicaid/medicaid-ncci-edit-files; https://www.cms.gov/medicare/coding-billing/ncci-medicaid

### M14. The repo's copy of the research brief overstates ClaimsSure and Audit Studio in Utah

**Where:** `01_PS3_research_brief.md:162` (repo copy): "An Acentra blog says ClaimsSure and Audit Studio help Utah move from reactive to proactive monitoring".

**Problem:** The source-of-truth brief corrects this line. The blog says the tools "have been successfully deployed across other states… (it does not say they are deployed in Utah)". Line 162 is the only difference between the repo copy and the source of truth.

**Replace with:** "An Acentra blog on Utah says ClaimsSure and Audit Studio 'have been successfully deployed across other states', helping states move from reactive to proactive monitoring (it does not say they are deployed in Utah)". Copy the updated brief in verbatim.

**Source:** https://acentra.com/blog/beyond-certification-how-utah-and-acentra-health-are-redefining-trust-and-accountability-in-medicaid-modernization; `/workspace/acentra-ps3/01_PS3_research_brief.md:162`.

### M15. Acentra product integration and branding are stated as fact

**Where:**
- `LandingPage.tsx:10`: "Built to sit downstream of eCAMS and feed an SIU".
- `LandingPage.tsx:17`: `{ value: "eCAMS", label: "Sits downstream of the claims engine" }`.
- `CLAIMSHIELD_NEXUS_PLAN.md:108`: "**Pitch:** ClaimShield Nexus sits downstream of eCAMS…".
- `IDEATION_AND_IMPROVEMENTS.md:104`: "Sits downstream of eCAMS-style claims systems via X12/FHIR adapters". No X12 or FHIR adapter exists in the repo.
- `frontend/index.html:7`: "ClaimShield Nexus — Acentra Health SIU".
- `frontend/src/components/Shell.tsx:43`: "SIU · post-adjudication · Acentra Health".
- `frontend/src/features/auth/LoginPage.tsx:64`: "Acentra Health SIU".
- `LandingPage.tsx:127`: "Accelerating better outcomes · program integrity". "Accelerating Better Outcomes" is Acentra's own homepage tagline.

**Problems:**
- eCAMS/RuleIT interfaces are not public, and the plan itself marks every integration point [ASSUMPTION] (plan L60, L106).
- Acentra's current claims solution page describes the CMS-certified **evoBrix X** platform.
- "Acentra Health SIU" implies an Acentra product or unit. Reusing the tagline implies endorsement.

**Replace with:**
- Landing L10 → "Designed to sit downstream of a claims adjudication system (e.g. eCAMS/evoBrix X-style) and feed an SIU; integration points are assumptions, as interfaces are not public."
- L17 → `{ value: "Adapter", label: "CSV / synthetic batch in; FHIR/X12 adapters planned" }`.
- Branding → "ClaimShield Nexus — student prototype for the Acentra Health Hackathon (PS3)".
- Drop the tagline, or attribute it ("inspired by Acentra's 'Accelerating Better Outcomes'").
- IDEATION L104 → "…via a canonical CSV today; FHIR/X12 adapters are planned".

**Source:** https://acentra.com/solutions (evoBrix X; "over 800 pre-built edits and audits"); https://acentra.com/technologies/ecams-hce; plan L60, L106.

### M16. The brief validator is hard-coded and the Limitations section is too thin

**Where:**
- `backend/src/claimshield/cases/workspace.py:691`: `"validator": {"checked": n_sents, "dropped": 0, "cited": n_cited}`.
- `frontend/src/features/workspace/BriefPanel.tsx:116-118`: "Validator: X/Y sentences cited, 0 dropped".
- `workspace.py:628-640` (Limitations: template only; masking) and `:684-685`.

**Problems:**
- `dropped` is always 0 and nothing is validated, yet the UI presents it as a grounding check.
- The brief (§8.2) and plan (X12, L260) require a real check: every cited ID exists and every number appears in the evidence pack.
- The Limitations section omits:
  - synthetic data;
  - no medical records reviewed;
  - possible legitimate explanations (for example, base rate plus mileage lines, or a date-of-death data lag);
  - that the priority score is uncalibrated (M1);
  - the rule and policy versions;
  - that this is not a determination of improper payment.

**Replace with:**
- Implement the check (resolve each cite ID against alerts and metrics, regex the numbers against the evidence pack, drop failures), or label the line "**Template brief — citations attached by construction; no automated validator in this build**".
- Add these Limitations sentences:
  - "Generated from synthetic data; no medical records were reviewed."
  - "Scores are heuristic and uncalibrated."
  - "Signals have common legitimate explanations; see evidence gaps."
  - "This brief is not a determination of improper payment or fraud; a human investigator decides."

**Source:** brief §8.2; plan L260; NIST AI 600-1: https://nvlpubs.nist.gov/nistpubs/ai/NIST.AI.600-1.pdf

### M17. "Synthetic NPIs pass Luhn" is mis-described, and the format looks real

**Where:**
- `README.md:69` and `backend/README.md:42`: "Synthetic NPIs pass Luhn."
- `backend/src/claimshield/synth/luhn.py:6-27` (plain Luhn, no 80840 prefix).
- `CLAIMSHIELD_NEXUS_PLAN.md:640`: "Luhn-valid".
- `data/reference/PAPERS.md:62`: "Luhn checksum".

**Problems:**
- The NPI check digit is Luhn applied with the `80840` prefix (equivalent to adding the constant 24). I checked all 48 seed NPIs: **none** is a valid NPI.
- That outcome is safe, but the README claim is technically wrong, and some seed values start with 1 or 2 (e.g. `2869189395`, `1110145164`), so they *look* like real NPIs.
- If someone "fixes" the algorithm, these become valid real-format NPIs that could belong to real providers.
- The task brief prefers an obviously synthetic format.

**Replace with:**
- Emit `NPI-SYN-0000123` style IDs (or 10 digits starting with 9).
- README → "Synthetic provider IDs use the NPI-SYN- prefix and are deliberately not valid NPIs (they fail the CMS NPI check digit), so they cannot collide with real providers."

**Source:** CMS, "Requirements for NPI and NPI Check Digit": https://www.cms.gov/Regulations-and-Guidance/Administrative-Simplification/NationalProvIdentStand/Downloads/NPIcheckdigit.pdf (local copy `/workspace/factcheck/npicd.pdf`); NPPES: https://download.cms.gov/nppes/NPI_Files.html

### M18. Capacity and "expected value" claims don't match the queue

**Where:**
- `LandingPage.tsx:29`: "Capacity is the control: 40 investigator hours".
- `LandingPage.tsx:199`: "watch harm / selected / needs-evidence fill 40 hours".
- `LandingPage.tsx:70`: "The queue sorts by expected value inside the hours you actually have."
- `backend/src/claimshield/pipeline/service.py:51-58`: reserves only `min(harm_hours, 35% × capacity)` for harm, then knapsacks the rest **on `composite`**, not on EV.
- `backend/src/claimshield/queue/knapsack.py:4-7`: EV adds λ·harm·members to dollars and is shown as "Expected value" (`WorkspacePage.tsx:260`, `ManagerQueuePage.tsx:599`).
- Observed in run: harm-lane cases total 34.5 h, the selected lane 25.5 h, and the needs-evidence lane 8.5 h. That is 60 h queued (68.5 h including needs-evidence) against a 40 h capacity. The highest-composite non-harm case (0.717, "Christopher Dominguez", 10 h) went to the backlog while three 0.55-composite volume cases were selected, because they pack better.

**Problems:**
- The page claims 40 hours but the queue holds about 60.
- The page claims EV ordering but the ranking uses composite.
- "Expected value" mixes dollars with harm points, so it is not a dollar figure.
- Packing efficiency is not explained, and a judge comparing columns will notice.

**Replace with:**
- Either cap total hours including the harm lane (and show "harm lane exceeds capacity by X h" as an explicit over-commit warning), or say "Priority-override cases are queued regardless of hours; the remaining capacity is packed."
- Landing L70 → "The queue packs the highest combined-priority cases into the remaining hours."
- Rename EV to "**Priority value (dollars + weighted harm, unitless)**", or show dollars and harm separately.
- Add a tooltip: "Selected by best fit of priority into hours; a higher-priority case can wait if it does not fit."

**Source:** brief §7 (capacity-aware ranking); plan L509.

### M19. The 45-day screening clock is attributed to the SIU and computed from the run date

**Where:**
- `LandingPage.tsx:25`: "…before the 45-day screening clock runs out".
- `LandingPage.tsx:34`: "Screening clock the SIU is racing".
- `LandingPage.tsx:147-148`: "Screening clock / 45 calendar days".
- `frontend/src/lib/format.ts:90-91`: "d left on 45-day screen".
- `ManagerQueuePage.tsx:562`, `:622`; `CaseDrawer.tsx:80`.
- `backend/src/claimshield/queue/rank.py:23`: "Urgency (horizon + 45-day clock)".
- `pipeline/service.py:225`: `sla_due = run date + 45` for every case.

**Problems:**
- The 45-day screening timeframe comes from CMS's Program Integrity Manual for CMS contractors (UPICs) screening leads. It is not a universal SIU rule; MCO SIU timelines are set by state contracts.
- Counting from the pipeline run date rather than lead receipt means every case shows the same days left, so the urgency factor carries no information.

**Replace with:**
- Landing L34 → `{ value: "45 days", label: "CMS PIM screening timeframe for UPIC leads; used here as a configurable SLA" }`.
- L25 → "…before the configured screening SLA (default 45 days, modelled on the CMS PIM) runs out."
- Compute the SLA from `lead_received_at` (earliest alert date) and make it configurable per state contract.

**Source:** CMS PIM ch. 3 (Medicaid investigations and audits): https://www.cms.gov/files/document/chapter-3-medicaid-investigations-audits.pdf; brief §2.

### M20. Pejorative or conclusory signal labels contradict "never prints the word fraud"

**Where:**
- `backend/src/claimshield/cases/workspace.py:101` ("Doctor shopping"), `:105` ("Clone billing"), `:107` ("Urban ambulance mileage padding"), `:113` ("Genetic-testing mill").
- `frontend/src/lib/format.ts:55`, `:59`, `:62` (same labels).
- `LandingPage.tsx:40`: "G1-style telefraud".
- `LandingPage.tsx:200`: "The product never prints the word fraud on a provider."

**Problem:** "Mill", "padding", "cloning" and "doctor shopping" are conclusions of intent, which is the same problem as calling a provider fraudulent. They appear next to a named provider in the queue and in briefs that could go into a referral. That undercuts the strong "potential FWA pattern" framing.

**Replace with:**
- "Multiple-prescriber opioid pattern (member-level)"
- "High same-day identical-service volume"
- "Ambulance mileage above urban reference"
- "Genetic-test ordering concentration vs peers"
- Landing L40 → "so a G1-style multi-NPI telehealth referral pattern is one case, not many tickets".

**Source:** brief §8 (neutral language; leads, not findings); CMS MLN Fraud & Abuse (fraud requires intent): https://www.cms.gov/outreach-and-education/medicare-learning-network-mln/mlnproducts/downloads/fraud-abuse-mln4649244.pdf

### M21. "Confirmed pattern" is written on decisions that confirmed nothing

**Where:**
- `backend/src/claimshield/wiki/service.py:111`: `"confirmed_pattern": pattern`. It is set for every decision, including `dismiss`, `monitor` and `needs_evidence`.
- `frontend/src/features/wiki/ProposalCard.tsx:47`: shown as "Pattern".

**Problem:** A dismissed or monitored case should never produce a "confirmed" precedent. If those reach the knowledge wiki, future briefs inherit them as precedents (feedback-loop bias; brief §8.3).

**Replace with:** Set `confirmed_pattern` only when the outcome is `substantiated`. Otherwise use `"observed_pattern"` with the decision attached ("dismissed — reason: …").

**Source:** brief §8.3 (precedents need human approval; avoid feedback loops).

---

## 2. MINOR (fix if time allows)

| # | Where | Current | Problem | Replace with | Source |
|---|---|---|---|---|---|
| m1 | `LandingPage.tsx:18` | "Built for special investigations, not pay-and-chase noise" | The product is post-adjudication, which is pay-and-chase by definition. | "Built for SIU case work after payment, prioritised for human review" | brief §2 |
| m2 | `LandingPage.tsx:27` | "Documentation errors swamp true schemes." | "Swamp" is unquantified. CMS says insufficient documentation was 77.17% of FY25 Medicaid improper payments and is "generally not indicative of fraud". | "In FY2025, 77% of Medicaid improper payments were insufficient documentation, which CMS says is generally not indicative of fraud." | https://www.cms.gov/files/document/2025-perm-medicaid-improper-payment-rates.pdf ; https://www.cms.gov/newsroom/fact-sheets/fiscal-year-2025-improper-payments-fact-sheet |
| m3 | `LandingPage.tsx:40` | "…one case, not twelve tickets" | The count of twelve is **[UNVERIFIED]**; it depends on the seed. | "…one case, not a dozen separate tickets (seed 7)", only after checking the count. | run logs |
| m4 | `LandingPage.tsx:44` | "Rural small-n peers show limited confidence. They do not auto-flag." | `anomaly/peer.py` still flags limited-confidence peers at z ≥ 3.2. | "…show limited confidence and need a stricter threshold (z ≥ 3.2) to flag." | code |
| m5 | `workspace.py:536`, `:547` | Overflow text "The case sits in Monitor…"; a selected case is recommended "Monitor pending investigator review…" | Collides with the `monitor` disposition. A selected (prioritised) case is told to "monitor". | Overflow → "Tracked backlog". Selected → "Open for investigator review…" | — |
| m6 | `queue/rank.py:91` | severity = max(harm, severity)/5 | Harm and severity are on a 1–4 scale, so the factor never reaches 1. | Divide by 4. | code |
| m7 | `rules/engine.py:44` (`_duplicates`) | Same member/provider/code/DOS | Ignores modifiers (e.g. 76/77, RT/LT, 59/X{EPSU}) and units, so legitimate repeats get flagged. | Key on modifiers; exclude repeat-procedure modifiers. | CMS NCCI policy manual (modifiers): https://www.cms.gov/medicare/coding-billing/ncci-medicaid |
| m8 | `rules.yaml` `policy_ref` (e.g. L6 `NCCI-SYN-DUP`, L66 `SIU-CLONE`, L71 `SCHRUPP-STAY`, L56 `CMS-POS`) | Opaque tags shown in briefs ("Policy OIG-DOD") | A judge cannot follow them. | Add a `policy_url` and human title per rule, shown in the brief. | — |
| m9 | `rules.yaml:79` | "Shared owner, TIN, or bank across multiple NPIs" | Code requires 2+ distinct strong edge kinds from owner/TIN/contact (`graph/build.py:62`); there is no bank edge. | "Two or more shared identifiers (owner, TIN, contact) across multiple NPIs" | code |
| m10 | `WorkspacePage.tsx:287`, `:306`; `ManagerQueuePage.tsx:761`; `InvestigatorCasesPage.tsx:234` | "linked NPIs" / "Case NPIs:" followed by `PRV-…` IDs | These are internal provider IDs, not NPIs. | "linked providers" / "Case providers" | — |
| m11 | `rules/engine.py:518`, `:536` | Urban mileage cap of 80 miles (`mileage_padding`) | Invented threshold presented as a cap. | Label it "synthetic reference (80 mi), not a CMS limit", or base it on a peer distribution. | **[UNVERIFIED]**; no CMS source |
| m12 | `rules/engine.py:164` | `daily_minutes_cap` > 960 min | Fine as a demo, but say why 16 h. | "Over 16 billed hours/day for one rendering provider (synthetic threshold; OIG ABA audits examined impossible-day patterns)" | OIG ABA reports in brief §3 |
| m13 | `rules/engine.py:196-198` | Inpatient overlap is inclusive of admit **and discharge** day | Home health often legitimately starts on the discharge day; outpatient services occur on the admit day. | Exclude the discharge day for HH; treat admit/discharge days as lower confidence. | **[UNVERIFIED]** for Medicaid; cite state policy |
| m14 | `rules.yaml:67-71`, `workspace.py:106` | "High-DRG facility claim with same-day admit and discharge" | Legitimate causes: transfer, death, leaving against medical advice. "Schrupp" models a German DRG system. | Add the discharge-status exclusion; say "German-DRG-inspired synthetic pattern". | PAPERS.md L14-15 |
| m15 | `workspace.py:116` | "six CURES elements" | Correct count, but name them: type of service, individual receiving, date, location, individual providing, start/end time. | "EVV records with the six 21st Century Cures Act data elements (service type, member, date, location, worker, start/end time)" | https://www.medicaid.gov/medicaid/home-community-based-services/guidance/electronic-visit-verification-evv |
| m16 | `backend/src/claimshield/cases/provenance.py:20` | "matched to rendering NPI or owner name" | Code matches the **billing** NPI. | "matched to billing-provider NPI or owner name" | code |
| m17 | `CLAIMSHIELD_NEXUS_PLAN.md:103` | mentions "800 pre-built edits and audits" | The source says "**over** 800" and ties it to the Claims, Encounters & Financial Management solution on **evoBrix X**, not to RuleIT or PI. | "…'over 800 pre-built edits and audits' (Claims, Encounters & Financial Management solution, CMS-certified evoBrix X platform)" | https://acentra.com/solutions |
| m18 | `CLAIMSHIELD_NEXUS_PLAN.md:104` | "ClaimsSure® (fraud detection) and Audit Studio® (audit optimisation)" | These are the team's characterisations, not quotes. | Mark them [INFERENCE], or quote Utah PRISM's "Audit Studio (Fraud and Abuse System)". | https://medicaid.utah.gov/prism/ |
| m19 | `IDEATION_AND_IMPROVEMENTS.md:91` | "…before going live, in the spirit of Acentra's RuleIT." | Pre-launch rule testing as a RuleIT feature is not in the sources. | "…before going live (our idea; RuleIT is described publicly only as a configurable edit/audit engine)" | https://acentra.com/technologies/ecams-hce |
| m20 | `CLAIMSHIELD_PLAN_DRAFT.md` (whole file) | Superseded draft with MAI and eCAMS errors | Judges may read the wrong plan. | Delete it or add a banner "SUPERSEDED by CLAIMSHIELD_NEXUS_PLAN.md". `README.md:13` links it. | — |
| m21 | `data/reference/PAPERS.md:15` | "~80% weighted F1 on the simulator" | Not in the brief. **[UNVERIFIED]** | Verify against the Schrupp paper or remove. | https://doi.org/10.1007/978-3-031-63772-8_22 |
| m22 | `PAPERS.md:17` | "Li, Huang, Ayvaci, Setia (M&SOM / related IS literature)" | Citation **[UNVERIFIED]**; no venue or year. | Give a full citation or remove. The GAO clause on the same line is verified. | — |
| m23 | `PAPERS.md:35` | "GAO catheter scheme 2023–24" | **[UNVERIFIED]**. The OIG telefraud SFA is verified. | Cite the DOJ/OIG catheter press release, or drop it. | https://oig.hhs.gov/documents/root/1045/sfa-telefraud.pdf |
| m24 | `PAPERS.md:56` | "Discrete-time hazard (Allison; Jenkins) — 30/60/90 confirmation risk" | No hazard model is implemented (M1). | "…planned; current build uses a heuristic placeholder" | — |
| m25 | Seed data `data/generated/tiny/*.csv` | Faker real-looking names (a member "Dr. Renee Cardenas", sex M; an org named "Suzanne Briggs"; an individual "Jennifer Watson" with specialty outpatient_hospital and sole_community); every exclusion DOB = 1965-03-12; real exclusion-type codes (1128b4, 1128a2) | Real-looking names next to "excluded" and "after death" invite "is this a real person?" questions; realism slips are visible on screen. | Prefix synthetic names ("SYN Provider 0142" / "Member M-…"); vary DOBs; keep the authority codes but add a "synthetic" banner. | brief §9 |
| m26 | `investigation.csv` / `synth/generator.py:591-592` | Unsubstantiated INV-SRXTXDZPHS recovered $10,084; education INV-PAARUF7W9V recovered $9,019.69 against $6,421.55 identified; hard negative HN1 has outcome "referred" | Amounts are drawn independently of outcome, so labels are internally inconsistent. | Recovery = 0 unless substantiated; recovered ≤ identified; hard negatives end unsubstantiated. | — |
| m27 | Seed EVV | One EVV lat/lon falls in the ocean. | Visible on any map. | Sample inside the synthetic county polygons. | — |
| m28 | `queue/knapsack.py:4-7` | EV projects run-rate `flagged·h/90` for every case | After-death and excluded-party lines do not "keep burning" once caught; projecting them inflates EV. | Project only recurring-pattern kinds. | — |
| m29 | `infra/lambda/claimshield-s3-processor/README.md:5` | "The fraud pipeline" | Contradicts the no-fraud-label language. | "The FWA lead-generation pipeline" | — |
| m30 | `docs/AWS_INGEST.md` | No data-handling note | Judges may ask about PHI in S3. | "Synthetic data only. Do not upload PHI; a real deployment needs a BAA, encryption and minimum-necessary access (45 CFR 164.514)." | https://www.ecfr.gov/current/title-45/subtitle-A/subchapter-C/part-164/subpart-E/section-164.514 |
| m31 | `backend/src/claimshield/api/main.py:40-45` | FastAPI title only | The OpenAPI page has no description or disclaimer. | `description="Synthetic-data prototype. Outputs are leads for human review, not determinations of fraud or improper payment."` | — |
| m32 | `frontend/src/features/audit/AuditPage.tsx:41` | "appends to an intact chain" | "Intact" is asserted, not checked on page load. | Show the result of a chain-verification call ("Chain verified at …"). | — |
| m33 | `README.md:3` | "Post-adjudication SIU platform for Medicaid-like FWA…" | "Platform" overstates a prototype. | "Post-adjudication SIU prototype (synthetic data)…" | — |

---

## 3. Already done well (keep, and say so in the pitch)

- **Language discipline.**
  - "Potential FWA pattern requiring investigation. This is not an automatic fraud label." (`workspace.py:1068`).
  - The brief action reads "Escalate for human review of a potential FWA pattern requiring investigation", and the limitation reads "Does not conclude fraud, waste, or abuse."
  - Brief text: "A flag is a reason to review evidence, not a finding of fraud."
- **Improper payments ≠ fraud**, with correct FY2025 numbers (6.12%, $37.39B) at `LandingPage.tsx:25`, `:143-144`. These match the CMS fact sheet.
- **Suspension framed as the state's call** in several places:
  - `DecisionBar.tsx:203`: "42 CFR 455.23 payment suspension is a recommendation. The state decides."
  - `LandingPage.tsx:85`.
  - Plan L84 and L254 ("refer for MFCU consideration") use the right wording, and the UI should copy it (M5).
- **No CPT.** HCPCS Level II A0425/A0427 plus SYNTH codes, enforced by a test. The A0425 cap of 250 matches the real Oct-2026 Medicaid practitioner MUE. This avoids the AMA CPT licensing question, which remains **[UNVERIFIED]** for a student demo (brief §11).
- **Medicaid MUE implemented per line**, which is correct for Medicaid. Only the docs are wrong (M13).
- **Peer anomaly hygiene.** Peer-group widening with confidence levels, `MIN_PEERS_RELAXED=5`, stricter z for small groups, and an OIG-style IQR fence for home health.
- **Graph rings need 2+ distinct strong link kinds** (`graph/build.py:62`), and comparison peers are excluded from cases. This reduces false rings from a single shared address.
- **Data card** (`data_card.json`) states "synthetic data, no medical records, labels partial and noisy" and calls base rates "design knobs, not prevalence estimates". Ground truth is kept out of features.
- **Human-in-the-loop controls.**
  - Overrides need a 20+ character reason.
  - Wiki precedents need approval.
  - There is a needs-evidence lane, and evidence gaps are listed per case.
  - Overflow is "not dismissal" (`overflow_is_dismissal: false`).
- **Minimum-necessary privacy.** Member IDs are masked, unmasking needs a role and is audited, and the audit log is hash-chained.
- **PAPERS.md cites GAO-26-107799 correctly** (CMS cannot deny a claim solely on analytics; leads go to UPICs).
- **No repo file attributes "800+ edits" to RuleIT.**

---

## 4. Unverifiable or open items (do not state these as fact)

- "One case, not twelve tickets": the count depends on the seed (m3).
- Schrupp et al. "~80% weighted F1" (m21); "Li, Huang, Ayvaci, Setia" (m22); "GAO catheter scheme 2023–24" (m23).
- That sex/age conflict edits live in OCE/MCE-type code editors rather than NCCI for **Medicaid** specifically. NCCI's two edit types are verified; the OCE/MCE location is not (M12).
- The exact wording of the PIM ch. 4 harm levels. It comes from the brief/factcheck notes; re-check before quoting (M3).
- Inpatient admit/discharge-day overlap policy varies by state (m13).
- Whether showing a few CPT numbers in a student demo needs an AMA licence (brief §11). The repo avoids CPT, so this is moot.
- ClaimsSure, Audit Studio and Navigator internals; whether eCAMS/RuleIT can export edit hits (brief §11; plan L58-60).

## 5. Sources used

- CMS FY2025 improper payments fact sheet: https://www.cms.gov/newsroom/fact-sheets/fiscal-year-2025-improper-payments-fact-sheet and PERM rates: https://www.cms.gov/files/document/2025-perm-medicaid-improper-payment-rates.pdf
- CMS Medicaid NCCI: https://www.cms.gov/medicare/coding-billing/ncci-medicaid and edit files: https://www.cms.gov/medicare/coding-billing/ncci-medicaid/medicaid-ncci-edit-files. Verified live: two edit types; Medicaid MUE is per line. The Oct-2026 MUE file in `/workspace/factcheck/` has no MAI column; A0425 = 250.
- CMS NPI check digit: https://www.cms.gov/Regulations-and-Guidance/Administrative-Simplification/NationalProvIdentStand/Downloads/NPIcheckdigit.pdf (HTTP 200 checked today)
- OIG LEIE: https://oig.hhs.gov/exclusions/leie-database-supplement-downloads/
- 42 CFR 455.23: https://www.ecfr.gov/current/title-42/chapter-IV/subchapter-C/part-455/subpart-A/section-455.23
- 42 CFR 438.608: https://www.ecfr.gov/current/title-42/chapter-IV/subchapter-C/part-438/subpart-H/section-438.608
- 42 CFR 455.436: https://www.ecfr.gov/current/title-42/chapter-IV/subchapter-C/part-455/subpart-E/section-455.436
- CMS Managed Care Fraud Referral Toolkit: https://www.cms.gov/files/document/managed-care-fraud-referral-toolkit.pdf
- CMS PIM ch. 3 (Medicaid): https://www.cms.gov/files/document/chapter-3-medicaid-investigations-audits.pdf and ch. 4: https://www.cms.gov/Regulations-and-Guidance/Guidance/Manuals/Downloads/pim83c04.pdf
- CMS R1877CP (gender/procedure conflict, KX / CC45): https://www.cms.gov/Regulations-and-Guidance/Guidance/Transmittals/downloads/R1877CP.pdf
- MACPAC provider payment (fee schedules): https://www.macpac.gov/subtopic/provider-payment/ ; lock-in programmes: https://www.macpac.gov/wp-content/uploads/2019/08/Pharmacy-and-Provider-Lock-in-Programs-in-Medicaid-Fee-for-Service.pdf
- GAO-26-107799: https://www.gao.gov/products/gao-26-107799 (quote verified: CMS "does not have the authority to deny an individual claim solely based on data analytics")
- Acentra solutions (verified live: "over 800 pre-built edits and audits", evoBrix X): https://acentra.com/solutions ; eCAMS HCE: https://acentra.com/technologies/ecams-hce ; Utah blog: https://acentra.com/blog/beyond-certification-how-utah-and-acentra-health-are-redefining-trust-and-accountability-in-medicaid-modernization ; Utah PRISM: https://medicaid.utah.gov/prism/
- OIG reports: OEI-02-17-00250 https://www.oig.hhs.gov/oei/reports/oei-02-17-00250.pdf ; OEI-09-12-00351 https://oig.hhs.gov/oei/reports/oei-09-12-00351.pdf ; telefraud SFA https://oig.hhs.gov/documents/root/1045/sfa-telefraud.pdf
- Medicaid EVV: https://www.medicaid.gov/medicaid/home-community-based-services/guidance/electronic-visit-verification-evv
- NIST AI RMF 100-1 and 600-1 (links above); AMA CPT licensing FAQ: https://www.ama-assn.org/practice-management/cpt/cpt-licensing-frequently-asked-questions-faqs
