# ClaimShield Nexus: Research Brief for Acentra Health Hackathon Problem 3

**Prepared for:** Panshul Arora and team (B.Tech Cybersecurity, SRM) and the engineering agent that will write the architecture
**Prepared on:** 8 October 2026 (IST). Sources were accessed 6–8 Oct 2026 unless a different date is given.
**Scope:** US healthcare payer fraud, waste and abuse (FWA), Medicaid program integrity, detection methods, data sources, how to rank cases, explainability, and a plan for synthetic data.

**How to read the labels**

| Label | Meaning |
|---|---|
| **[VERIFIED]** | I read this in the primary source at the link: a government page or manual, a regulation, the original paper, or a dataset file I downloaded and inspected. |
| **[SUPPORTED]** | Backed by a credible secondary source, or by a primary source I could only see in part (an abstract, a search snippet, or a citing paper). |
| **[INFERENCE]** | My own reasoning or design recommendation. It is not a fact from a source. |
| **[UNCERTAIN]** | I could not settle this. These items are repeated in §11, "Unverified / open questions". |

---

## 0. Executive summary (one page)

**The problem.** Health payers lose money to three things:
- **Fraud**: knowingly submitting false claims, or paying kickbacks for referrals.
- **Abuse**: practices that create unnecessary costs, such as upcoding (billing a more expensive code than the service justifies) or billing for unnecessary services.
- **Waste**: inefficiency, such as excessive diagnostic tests.

These definitions come from the CMS (Centers for Medicare & Medicaid Services) training booklet [MLN4649244, Apr 2026](https://www.cms.gov/outreach-and-education/medicare-learning-network-mln/mlnproducts/downloads/fraud-abuse-mln4649244.pdf) [VERIFIED].

For fiscal year (FY) 2025, CMS estimated Medicaid **improper payments** at 6.12%, or $37.39 billion. CMS also says 77.17% of that came from insufficient documentation, which is "generally not indicative of fraud or abuse" ([CMS FY2025 fact sheet](https://www.cms.gov/newsroom/fact-sheets/fiscal-year-2025-improper-payments-fact-sheet)) [VERIFIED]. **An improper payment is not the same thing as fraud.** Judges may test whether you know the difference.

**The users.** A payer's SIU (Special Investigations Unit), or a state Medicaid PI (program integrity) unit, works leads through a fixed sequence:
1. Take in and screen leads.
2. Open investigations.
3. Recover overpayments and educate providers.
4. Refer suspected fraud to the state MFCU (Medicaid Fraud Control Unit) or to law enforcement.

Federal rules require a preliminary investigation, then a full investigation, then a documented resolution, with due process throughout ([42 CFR 455.13–455.16](https://www.ecfr.gov/current/title-42/chapter-IV/subchapter-C/part-455/subpart-A)) [VERIFIED]. CMS's own Medicaid contractors must finish screening a lead within 45 calendar days ([Medicaid PI Manual ch. 3](https://www.cms.gov/files/document/chapter-3-medicaid-investigations-audits.pdf)) [VERIFIED].

The scarce resource is **investigator time**. Every false positive wastes that time and can hurt a legitimate provider.

**Why Acentra cares.** Acentra's product line maps closely onto ClaimShield Nexus, so reuse its vocabulary:
- **ClaimsSure®** and **Audit Studio®**: CMS's list of vendor pledges describes them as "Pre- and post-payment analytics, audit workflow management, and tools supporting fraud, waste, and abuse detection and audit readiness". Acentra is offering both to states at no licence cost through 2028 ([Medicaid.gov pledges](https://www.medicaid.gov/resources-for-states/working-families-tax-cut-legislation/community-engagement/pledges-from-medicaid-tech-companies)) [VERIFIED].
- **RuleIT™**, a rules engine ([eCAMS HCE](https://acentra.com/technologies/ecams-hce)) [VERIFIED].
- **Navigator**, a knowledge tool marketed as giving "source-backed answers" ([acentra.com/solutions](https://acentra.com/solutions)) [VERIFIED].

**What to build (recommended).** [INFERENCE]
1. **A deterministic rules layer** with reason codes. It checks for:
   - duplicate claims;
   - NCCI (National Correct Coding Initiative) PTP (procedure-to-procedure) pair edits and MUE (medically unlikely edit) unit limits;
   - services billed after the member's death;
   - more than 24 billable hours in a day;
   - services that overlap an inpatient stay;
   - excluded providers.
2. **Peer-group anomaly scoring.** Robust z-scores, plus the "75th percentile + 1.5×IQR" outlier fence that the OIG (HHS Office of Inspector General) itself used ([OIG home health report](https://oig.hhs.gov/documents/evaluation/2847/OEI-04-11-00240-Complete%20Report.pdf)) [VERIFIED], plus an Isolation Forest. IQR = interquartile range.
3. **Graph analytics** on a provider–member–location–owner graph: Leiden communities, shared-address and shared-owner links, and PageRank-style risk propagation. The evidence for this design:
   - A peer-reviewed study found that ordinary ML with provider–beneficiary centrality features (such as PageRank) beat the best GNN (graph neural network) it tested ([Yoo, Shin & Kyeong 2023](https://doi.org/10.1109/ACCESS.2023.3305962)) [VERIFIED].
   - Another found that risk propagated through shared locations drove most of the accuracy in predicting OIG exclusions ([Branting et al. 2016](https://doi.org/10.1109/ASONAM.2016.7752336)) [SUPPORTED].
4. **A 30/60/90-day risk model** framed as a discrete-time hazard model. Evaluate it with strict temporal back-testing, PR-AUC (area under the precision–recall curve), precision at investigator capacity, and calibration.
5. **A capacity-aware SIU queue.** Score each case as expected recoverable dollars plus a patient-harm term, then fill the available investigator-hours (a knapsack problem). Patient-harm cases always go first. This mirrors CMS's own 1–4 scoring of likelihood, patient harm, financial impact and breadth ([Medicare PIM ch. 4 §4.13](https://www.cms.gov/Regulations-and-Guidance/Guidance/Manuals/Downloads/pim83c04.pdf)) [VERIFIED].
6. **An LLM-written investigation brief** grounded only in a JSON evidence pack. Every sentence cites claim, rule or statistic IDs. A validator rejects uncited or invented numbers, and a template brief is the fallback. Two more pieces close the loop that the Acentra masterclass described: a **precedent wiki** following Karpathy's "LLM Wiki" pattern, and a **hash-chained, append-only audit log**.

**Biggest risks** [INFERENCE unless cited]:
- **Planted fraud that is trivially detectable** in your own synthetic data.
- **Temporal leakage**: using information that would not exist at prediction time.
- **CPT® licensing.** CPT is copyrighted by the AMA (American Medical Association), which says any use requires a licence ([AMA FAQ](https://www.ama-assn.org/practice-management/cpt/cpt-licensing-frequently-asked-questions-faqs)) [VERIFIED]. Prefer public HCPCS Level II codes plus synthetic codes.
- **Overclaiming accuracy.** A 2025 review found "few to no works which establish benchmarks across diverse techniques", with reported F1 ranging from 0.15 to 0.948 ([Curtis et al. 2025](https://link.springer.com/article/10.1186/s40537-025-01295-3)) [VERIFIED].

---

## 1. The problem and its users

### 1.1 Key terms

- **Payer**: the organization that pays claims. That can be a state Medicaid agency, Medicare, a commercial insurer, or a Medicaid **MCO** (managed care organization: a private plan that the state pays a fixed monthly "capitation" amount per member).
- **Claim**: a bill from a provider.
  - Types: professional (clinician), institutional (hospital/facility) and pharmacy.
  - A claim has header fields (member, billing provider, dates) and line items (procedure code, units, charge, paid amount).
- **NPI** (National Provider Identifier): the 10-digit ID for US providers. It is issued through **NPPES** (National Plan and Provider Enumeration System) ([NPPES downloads](https://download.cms.gov/nppes/NPI_Files.html)) [VERIFIED].
- **HCPCS** (Healthcare Common Procedure Coding System):
  - Level I is **CPT** (Current Procedural Terminology), owned by the AMA.
  - Level II is maintained by CMS and covers supplies, DME (durable medical equipment), ambulance, drugs and similar items. The CMS file deliberately excludes CPT for copyright reasons ([CMS HCPCS readme](https://www.cms.gov/files/document/2020-hcpcs-alpha-numeric-hcpcs-readme-file.txt)) [VERIFIED].
- **FFS**: fee-for-service, meaning the payer pays per claim.
- **LEIE**: OIG's List of Excluded Individuals/Entities, explained in §4.

### 1.2 What fraud, waste and abuse mean

CMS shows four causes of improper payment, from honest to criminal [VERIFIED]:
- **mistakes**, which cause errors;
- **inefficiencies**, which cause waste;
- **bending the rules**, which causes abuse;
- **intentional deceptions**, which cause fraud.

CMS adds: "The difference between fraud and abuse depends on specific facts, circumstances, intent, and knowledge" ([MLN4649244](https://www.cms.gov/outreach-and-education/medicare-learning-network-mln/mlnproducts/downloads/fraud-abuse-mln4649244.pdf)) [VERIFIED].

The main federal laws, all named in the same booklet [VERIFIED]:
- the False Claims Act;
- the Anti-Kickback Statute (AKS);
- the Physician Self-Referral Law ("Stark");
- the Exclusion Statute;
- the Civil Monetary Penalties Law.

**Design implication [INFERENCE]:** the system should never label anyone as "fraud". Its output is "patterns that warrant human review". Intent is a legal finding made by people and courts.

### 1.3 Scale (state each number precisely)

| Figure | What it is, and what it is not | Source |
|---|---|---|
| Medicaid improper payment rate FY2025: **6.12% ($37.39B)**, up from 5.09% in FY2024 | **Not a fraud measure.** CMS says improper payment measurement "is not a measure of fraud", and 77.17% was insufficient documentation | [CMS fact sheet](https://www.cms.gov/newsroom/fact-sheets/fiscal-year-2025-improper-payments-fact-sheet) [VERIFIED] |
| PERM (Payment Error Rate Measurement) components: FFS 4.60%, **managed care 0.00%**, eligibility 4.42% | The managed care component checks whether states paid capitation correctly. GAO (Government Accountability Office) reports that it does not review plans' payments to providers, so it can understate risk | [CMS 2025 PERM rates](https://www.cms.gov/files/document/2025-perm-medicaid-improper-payment-rates.pdf) [VERIFIED]; [GAO-25-107770](https://www.gao.gov/products/gao-25-107770) [SUPPORTED] |
| Medicare FFS FY2025: 6.55% ($28.83B); Part C 6.09% ($23.67B); Part D 4.00% ($4.23B) | Improper payments, not fraud | [CMS fact sheet](https://www.cms.gov/newsroom/fact-sheets/fiscal-year-2025-improper-payments-fact-sheet) [VERIFIED] |
| Fraud costs "tens of billions of dollars each year". A conservative estimate is 3% of health spending; some agencies say up to 10%, which "could mean more than $300 billion" | An **estimate** by NHCAA (National Health Care Anti-Fraud Association), not a measurement | [NHCAA](https://www.nhcaa.org/tools-insights/about-health-care-fraud/the-challenge-of-health-care-fraud/) [VERIFIED] |
| MFCUs, FY2025: 53 units; about $2B recovered; $4.64 returned per $1 spent; 1,185 convictions; **5,991 fraud referrals from managed care entities** | Enforcement outcomes | [OIG OEI-09-26-00140](https://oig.hhs.gov/reports/all/2026/medicaid-fraud-control-units-annual-report-fiscal-year-2025/) [VERIFIED] |
| DOJ 2025 National Takedown: 324 defendants, **$14.6B intended loss**. 2026 Takedown (23 Jun 2026): 455 defendants, over $6.5B; CMS suspended 1,079 providers and revoked 1,403 | **Alleged** (charged, not convicted) | [DOJ 2025](https://www.justice.gov/opa/pr/national-health-care-fraud-takedown-results-324-defendants-charged-connection-over-146); [DOJ 2026](https://www.justice.gov/opa/pr/national-health-care-fraud-takedown-results-455-defendants-charged-connection-over-65) [VERIFIED] |

### 1.4 Who does program integrity in Medicaid

- **State Medicaid agency PI unit.** Its duties under federal rules:
  - Have methods to identify suspected fraud, investigate without infringing legal rights and "afford due process", and refer cases to law enforcement ([42 CFR 455.13](https://www.ecfr.gov/current/title-42/chapter-IV/subchapter-C/part-455/subpart-A)) [VERIFIED].
  - Verify with beneficiaries whether billed services were actually received (§455.20, same link) [VERIFIED].
  - Check the LEIE, NPPES and the SSA (Social Security Administration) Death Master File, and check the LEIE at least monthly ([42 CFR 455.436](https://www.ecfr.gov/current/title-42/chapter-IV/subchapter-C/part-455/subpart-E/section-455.436)) [VERIFIED].
- **MFCUs.** They operate in all 50 states, DC, Puerto Rico and the US Virgin Islands. They usually sit in the state Attorney General's office, separate from the Medicaid agency, and are overseen by OIG ([OIG MFCU page](https://oig.hhs.gov/fraud/medicaid-fraud-control-units-mfcu/)) [VERIFIED].
- **MCO compliance programs and SIUs.** Plans must promptly refer suspected fraud to the state ([42 CFR 438.608](https://www.ecfr.gov/current/title-42/chapter-IV/subchapter-C/part-438/subpart-H/section-438.608)) [VERIFIED]. CMS "encourages 'prompt' to be defined as within two business days" ([CMS Managed Care Fraud Referral Toolkit](https://www.cms.gov/files/document/managed-care-fraud-referral-toolkit.pdf)) [VERIFIED].
- **CMS contractors.**
  - **UPICs** (Unified Program Integrity Contractors) run data analysis and screen, vet, investigate and refer leads for Medicare and Medicaid ([Medicaid PIM ch. 3](https://www.cms.gov/files/document/chapter-3-medicaid-investigations-audits.pdf)) [VERIFIED].
  - **Medicaid RACs** (Recovery Audit Contractors), created by Affordable Care Act §6411, are state-run, paid on contingency fees, and subject to provider appeals ([CMS Medicaid RAC FAQ](https://www.cms.gov/medicare-medicaid-coordination/fraud-prevention/medicaidintegrityprogram/downloads/medicaid_rac_faq.pdf)) [VERIFIED].
- **Commercial insurers.** The NAIC (National Association of Insurance Commissioners) model law calls for anti-fraud initiatives, and an SIU is one option ([NAIC Model 680](https://content.naic.org/sites/default/files/model-law-680.pdf)) [SUPPORTED]. New York's guidelines ask insurers' SIU plans for "An assessment of optimal caseload per investigator" ([NY DFS guidelines](https://www.dfs.ny.gov/system/files/documents/2022/11/ffp_guidelines_20221115.pdf)) [VERIFIED]. So investigator capacity is a regulatory concept, not just an engineering one.

### 1.5 Typical workflow the product must support

Stages 1–4 below come from the CMS UPIC procedure in [Medicaid PIM ch. 3](https://www.cms.gov/files/document/chapter-3-medicaid-investigations-audits.pdf). Stages 5–9 come from regulation and the Medicare manual.

| Stage | What happens | Sourced detail |
|---|---|---|
| 1. Lead intake | Sources include data analysis, the state, Medicare, law enforcement or the OIG hotline, CMS, and general tips or news | PIM ch. 3 [VERIFIED] |
| 2. Proactive data project | Outlier analysis produces an "Analytic Findings Report" with the total dollars at risk. **Dollars at risk count only the outlier service codes**, not total billing. Projects generally need exposure above **$50,000** (or above the audit cost); this does not apply when fraud is suspected or to projects like opioid prescribing. Data is refreshed "at least every 30 days" | PIM ch. 3 [VERIFIED] |
| 3. Screening | "Screening shall be completed within 45 calendar days after receipt of the lead." Activities: enrollment and LEIE checks, data analysis, beneficiary interviews, site verification, **with no contact with the provider**. Suspected beneficiary harm is reported to CMS within 2 business days: "CMS has a zero tolerance for beneficiary harm issues" | PIM ch. 3 [VERIFIED]; preliminary investigation duty in [42 CFR 455.14](https://www.ecfr.gov/current/title-42/chapter-IV/subchapter-C/part-455/subpart-A) [VERIFIED] |
| 4. Vetting | CMS and the state are consulted before an investigation opens. The state gets "two weeks (14 calendar days) to respond" | PIM ch. 3 [VERIFIED] |
| 5. Full investigation | Provider contact, record requests (30 days to produce, plus an optional 15-day extension), medical review, sampling. Medicare UPICs should determine the nature and magnitude of the issue "within 210 calendar days" | [42 CFR 455.15](https://www.ecfr.gov/current/title-42/chapter-IV/subchapter-C/part-455/subpart-A); PIM ch. 3; [Medicare PIM ch. 4](https://www.cms.gov/Regulations-and-Guidance/Guidance/Manuals/Downloads/pim83c04.pdf) [VERIFIED] |
| 6. Resolution | Close, or resolve administratively: warning letter (education), suspension or termination, recovery of overpayments, other sanctions | [42 CFR 455.16](https://www.ecfr.gov/current/title-42/chapter-IV/subchapter-C/part-455/subpart-A) [VERIFIED] |
| 7. Referral | Suspected fraud goes to the MFCU. After a payment suspension, the referral must be made by the next business day | [42 CFR 455.21, 455.23](https://www.ecfr.gov/current/title-42/chapter-IV/subchapter-C/part-455/subpart-A) [VERIFIED] |
| 8. Payment suspension | Required on a "credible allegation of fraud" unless there is good cause. Good cause includes protecting access when the provider is the sole community provider or serves an underserved area. Notice within 5 days (law enforcement can ask to delay it up to 90 days). Suspension is temporary. Records are kept 5 years | [42 CFR 455.23](https://www.ecfr.gov/current/title-42/chapter-IV/subchapter-C/part-455/subpart-A/section-455.23) [VERIFIED] |
| 9. Prepayment controls | Medicare's FPS (Fraud Prevention System) applies prepayment edits and runs post-payment models that produce prioritized leads | [CMS FPS2 leaflet](https://www.cms.gov/files/document/dasg-leaflet-fps2.pdf) [VERIFIED] |

**Roles** [SUPPORTED by the manuals; role split is INFERENCE]:
- **Investigator**: works the case through interviews, records and findings.
- **SIU or PI manager**: prioritizes and assigns work. CMS: "investigations with the greatest program impact and/or urgency are given the highest priority" ([PIM ch. 4](https://www.cms.gov/Regulations-and-Guidance/Guidance/Manuals/Downloads/pim83c04.pdf)) [VERIFIED].
- **Clinical or coding reviewer**: judges medical necessity and coding. CMS lists record-review red flags including nearly identical documentation across patients, a trend toward high-end codes, and more hours billed than a workday allows (same source) [VERIFIED].
- **Data analyst**: NY DFS lists data analysts as SIU support staff ([NY DFS](https://www.dfs.ny.gov/system/files/documents/2022/11/ffp_guidelines_20221115.pdf)) [VERIFIED].

**Constraints to design for** [INFERENCE grounded in the sources above]:
1. **Limited capacity**, plus a 45-day screening clock.
2. **Harm from false positives.** Suspending a provider can cut off patients' access to care, which is why the suspension rule has good-cause exceptions.
3. **Due process.**
4. **Documentation.** PIM ch. 3 lists required case-file items, including lead source, dates, actions and the number of prior leads on the provider [VERIFIED]. These map directly to an audit-log schema.

---

## 2. Acentra Health relevance

| Item | What the sources say | Status |
|---|---|---|
| Company | Formed in 2023 from the merger of CNSI and Kepro. HQ in McLean, VA; 32 US offices plus Chennai, India; about 3,300 employees. Systems process about 1.8B claims and $48B in payments a year | [acentra.com/about-us](https://acentra.com/about-us) [VERIFIED] |
| **ClaimsSure® + Audit Studio®** | "Pre- and post-payment analytics, audit workflow management, and tools supporting fraud, waste, and abuse detection and audit readiness", licensed free to states through 2028 | [Medicaid.gov pledges](https://www.medicaid.gov/resources-for-states/working-families-tax-cut-legislation/community-engagement/pledges-from-medicaid-tech-companies) [VERIFIED] |
| Audit Studio in Utah | Utah's PRISM Medicaid system lists "Audit Studio (Fraud and Abuse System)" as a component. An Acentra blog says ClaimsSure and Audit Studio help Utah move from reactive to proactive monitoring | [Utah PRISM](https://medicaid.utah.gov/prism/) [VERIFIED]; [Acentra blog](https://acentra.com/blog/beyond-certification-how-utah-and-acentra-health-are-redefining-trust-and-accountability-in-medicaid-modernization) [VERIFIED] |
| ClaimsSure training | A Utah course page promises to cover how improper billing is detected and "four factors that predict anomalies in billing". **The four factors are not described publicly** | [Utah DHHS](https://medicaid.utah.gov/document/introduction-to-claimssure/) [VERIFIED page; content UNCERTAIN] |
| ClaimsSure history | A 2017 article reports that Michigan's MMIS (Medicaid Management Information System) used ClaimsSure to flag claims in real time for manual review by the state case-management team, using logistic-regression opioid models | [MedCity News 2017](https://medcitynews.com/2017/02/predictive-analytics-can-tackle-opioid-crisis/) [SUPPORTED; author affiliation not verified] |
| **RuleIT™** in eCAMS HCE | A configurable edit-and-audit engine that includes duplicate detection, with manual review only for exceptions (validation failures, potential duplicates, unusual billing patterns) and audit trails | [eCAMS HCE](https://acentra.com/technologies/ecams-hce) [VERIFIED] |
| Solutions page | A Program Integrity offering using ML and analytics for FWA, anomalies and predictive risk; "800+ pre-built edits and audits"; Navigator ("source-backed answers" from memos and policies); AI-assisted reviews with a human in the loop; a statement that higher-risk generative-AI uses need governance and human oversight | [acentra.com/solutions](https://acentra.com/solutions) [VERIFIED]. **Internals of the PI module and Navigator: UNCERTAIN** |
| NAMPI 2025 | NAMPI is the National Association for Medicaid Program Integrity. Acentra co-presented "Gateway to the Future: How AI Transforms Government Healthcare Programs" (26 Aug 2025) with its Chief AI & Analytics Officer and Arizona Medicaid's (AHCCCS) CIO | [Acentra event page](https://acentra.com/events/national-association-for-medicaid-program-integrity-nampi-2025) [VERIFIED] |
| **FEI Systems acquisition** | Announced 5 Aug 2026. Adds platforms for LTSS (long-term services and supports), HCBS (home- and community-based services) and behavioral health. No program-integrity link is stated | [Acentra press release](https://acentra.com/news/acentra-health-acquires-fei-systems) [VERIFIED] |

**Why FEI matters for PS3 [INFERENCE].** Home health, personal care and behavioral health are all named in the problem statement. In FY2025, MFCU fraud convictions involved personal care services attendants more often than any other provider type ([OIG MFCU FY2025](https://oig.hhs.gov/reports/all/2026/medicaid-fraud-control-units-annual-report-fiscal-year-2025/)) [VERIFIED]. A demo scheme involving HCBS or personal care, with EVV (Electronic Visit Verification) data, would line up with Acentra's newest business.

**Masterclass alignment [INFERENCE].** The speakers described a loop: capture expertise → resolve case → approve outcome → reuse precedent → evidence → AI reasoning. They also described an "AI-maintained knowledge wiki". Both match Karpathy's LLM Wiki gist, which has three parts:
- immutable raw sources;
- an LLM-maintained wiki with an `index.md` catalog and an append-only `log.md`;
- a schema file that tells the LLM how to maintain the wiki.

It runs three operations: ingest, query and lint ([gist](https://gist.github.com/karpathy/442a6bf555914893e9891c11519de94f)) [VERIFIED]. It also fits Navigator's "source-backed answers" positioning. Design details are in §8.4.

---

## 3. FWA scheme taxonomy with signals and data fields

The "Method" column uses these codes: R = rule, A = anomaly/peer comparison, T = temporal, G = graph, M = supervised ML. Field names refer to the synthetic schema in §9 [INFERENCE]. All "Signal" entries are my proposed implementations [INFERENCE] unless a source is cited.

| # | Scheme | Public example (source) | Prototype signal | Key fields | Method |
|---|---|---|---|---|---|
| 1 | **Duplicate billing** | OIG New Hampshire audit: suspect duplicates (same recipient, date, procedure) paid after staff overrides ([A-01-04-00003](https://oig.hhs.gov/documents/audit/3432/A-01-04-00003-Complete%20Report.pdf)) [VERIFIED]. NY members holding multiple Medicaid IDs ([A-02-18-01020](https://oig.hhs.gov/documents/audit/6451/A-02-18-01020-Report%20in%20Brief.pdf)) [SUPPORTED] | Exact duplicates (same member, provider, code, modifier, date). Near-duplicates (different modifier, units or rendering NPI). Member entity resolution (same name and date of birth under several IDs) | member_id, billing/rendering NPI, code, modifiers, dos, units, paid | R |
| 2 | **Upcoding** (E/M level creep; E/M = evaluation and management, i.e. office-visit codes) | OIG: 1,669 physicians billed the two highest E/M levels in ≥95% of visits. **OIG did not conclude this was inappropriate** ([OEI-04-10-00180](https://oig.hhs.gov/oei/reports/oei-04-10-00180.pdf)) [VERIFIED]. Misuse of modifier 25 is a CMS upcoding example ([MLN](https://www.cms.gov/outreach-and-education/medicare-learning-network-mln/mlnproducts/downloads/fraud-abuse-mln4649244.pdf)) [VERIFIED] | Share of top-two levels vs specialty peers. Shift in level mix over time. High level with a low-complexity diagnosis | specialty, em_level, dx, modifiers | A, T, M |
| 3 | **Unbundling** | NCCI PTP edits list code pairs that should not normally be billed together ([CMS NCCI Medicaid](https://www.cms.gov/medicare/coding-billing/ncci-medicaid)) [VERIFIED] | Same member, provider and day; the pair is in the PTP table with modifier indicator 0, or indicator 1 with a bypass-modifier rate far above peers | code pairs, dos, modifiers | R, A |
| 4 | **Excess units** | MUEs cap units per code. Medicaid applies them **per claim line** ([CMS](https://www.cms.gov/medicare/coding-billing/ncci-medicaid/medicaid-ncci-edit-files)) [VERIFIED] | units > MUE. Example from the Oct-2026 Medicaid practitioner MUE file: A0425 (ground ambulance mileage) = 250 (my own inspection of the file) [VERIFIED] | code, units | R |
| 5 | **Phantom services / after death** | OIG: capitation paid for deceased enrollees, over $249M in 14 states ([OIG 2023](https://oig.hhs.gov/reports/all/2023/multiple-states-made-medicaid-capitation-payments-to-managed-care-organizations-after-enrollees-deaths/)) [SUPPORTED]. A 2026 hospice owner allegedly bought data on recently deceased people and billed "a few days of hospice services" with back-dated records ([DOJ 2026](https://www.justice.gov/opa/pr/national-health-care-fraud-takedown-results-455-defendants-charged-connection-over-65)) [VERIFIED] | dos > date_of_death. "Ghost members" with no other care anywhere. Services the member denies in verification (§455.20) | member.dod, dos | R, A |
| 6 | **Excessive utilization** | OIG home health: six measures (outlier payments, visits, shared beneficiaries, late episodes, therapy visits, payments per beneficiary); outlier = above the 75th percentile + 1.5×IQR ([OEI-04-11-00240](https://oig.hhs.gov/documents/evaluation/2847/OEI-04-11-00240-Complete%20Report.pdf)) [VERIFIED] | Per-provider aggregates vs specialty × region peers, using the IQR fence or robust z (median/MAD; MAD = median absolute deviation) | specialty, region, aggregates | A |
| 7 | **Impossible timing** | Illinois Medicaid: claims for "500 or more hours of counseling and therapy services per day", with patients hospitalized elsewhere on billed days ([DOJ 2026](https://www.justice.gov/opa/pr/national-health-care-fraud-takedown-results-455-defendants-charged-connection-over-65)) [VERIFIED]. NY social adult day care billed hundreds of beneficiaries a day against a permitted occupancy of 30 (same) [VERIFIED]. Classic court case: *U.S. v. Krizek* ([Justia](https://law.justia.com/cases/federal/appellate-courts/F3/192/1024/594113/)) [SUPPORTED] | (a) Timed minutes per rendering NPI per day > 24h (or above a plausible ceiling). (b) Home or behavioral health service during an inpatient stay. (c) Billed headcount above facility capacity | rendering NPI, units, minutes, admit/discharge, capacity | R, T |
| 8 | **DME fraud** | Operation Gold Rush: foreign straw owners bought dozens of DME companies and billed **$10.6B** (mostly urinary catheters) using stolen identities of over 1 million Americans. It was caught by proactive data analytics, and Medicare paid about $41M of about $4.45B submitted ([DOJ 2025](https://www.justice.gov/opa/pr/national-health-care-fraud-takedown-results-324-defendants-charged-connection-over-146)) [VERIFIED] | New supplier with a billing spike. Members with no prior relationship to the ordering provider. Member IDs shared across new suppliers. Recent ownership change | supplier enroll_date, ordering NPI, owner links | T, G, A |
| 9 | **Ambulance** | OIG: $30M for transports where beneficiaries "did not receive Medicare services at the pick-up or drop-off locations, or anywhere else"; "about one in five suppliers had questionable billing" ([OEI-09-12-00351](https://oig.hhs.gov/oei/reports/oei-09-12-00351.pdf)) [VERIFIED] | Transport with no destination claim that day. Urban mileage outliers. Repeated dialysis transports. Members shared across suppliers | A04xx codes, mileage units, destination claims | R, A, G |
| 10 | **Lab / genetic testing** | OIG alert: tests not medically necessary or not ordered by a treating physician, marketed through telemarketing, health fairs and free cheek swabs ([OIG](https://www.oig.hhs.gov/fraud/consumer-alerts/fraud-alert-genetic-testing-scam/)) [VERIFIED]. 2025 takedown: 49 defendants, $1.17B in telemedicine and genetic testing ([DOJ](https://justice.gov/opa/pr/national-health-care-fraud-takedown-results-324-defendants-charged-connection-over-146)) [VERIFIED] | Ordering provider never saw the member. Distant telehealth-only orderer. Many members funnelled to one lab | ordering NPI, prior_visit_flag, lab NPI | G, R |
| 11 | **Home health / personal care** | EVV must capture six elements: service type, individual, date, location, provider, and start/end times ([Medicaid.gov EVV](https://www.medicaid.gov/medicaid/home-community-based-services/guidance/electronic-visit-verification-evv)) [VERIFIED]. 2026: an Alaska aide allegedly billed care while the recipient was hospitalized ([DOJ 2026](https://www.justice.gov/opa/pr/national-health-care-fraud-takedown-results-455-defendants-charged-connection-over-65)) [VERIFIED] | Claim with no EVV record. EVV location ≠ member's home. One aide in overlapping visits. Visits during an inpatient stay | evv start/end, lat/lon, aide_id | R, T |
| 12 | **Behavioral health / ABA** (ABA = applied behavior analysis, an autism therapy) | OIG ABA audits: Indiana ≥$56M improper ([OIG](https://oig.hhs.gov/reports/all/2024/indiana-made-at-least-56-million-in-improper-fee-for-service-medicaid-payments-for-applied-behavior-analysis-provided-to-children-diagnosed-with-autism/)), Wisconsin ≥$18.5M ([OIG](https://oig.hhs.gov/reports/all/2025/wisconsin-made-at-least-185-million-in-improper-fee-for-service-medicaid-payments-for-applied-behavior-analysis-provided-to-children-diagnosed-with-autism/)) [VERIFIED]. Arizona: about $650M substance-use treatment scheme with kickbacks for recruiting homeless and Native American patients ([DOJ 2025](https://www.justice.gov/opa/pr/national-health-care-fraud-takedown-results-324-defendants-charged-connection-over-146)) [VERIFIED] | Hours per clinician per day. Sessions during an inpatient stay. Influx of members from one address or recruiter | rendering NPI, units, member address clusters | R, T, G |
| 13 | **Pharmacy** (doctor shopping, pill mills) | OIG "doctor shopping": average daily MED (morphine equivalent dose) >120 mg for ≥3 months **and** ≥4 prescribers **and** ≥4 pharmacies, which flagged 22,308 beneficiaries ([OEI-02-17-00250](https://www.oig.hhs.gov/oei/reports/oei-02-17-00250.pdf)) [VERIFIED]. State lock-in thresholds vary, with no consensus ([MACPAC](https://www.macpac.gov/wp-content/uploads/2019/08/Pharmacy-and-Provider-Lock-in-Programs-in-Medicaid-Fee-for-Service.pdf)) [VERIFIED] | Member: distinct prescribers and pharmacies over 90 days, plus MED. Prescriber: opioid share vs peers. Pharmacy: share of distant members | ndc, days_supply, mme, prescriber, pharmacy | R, A, G |
| 14 | **Kickback / referral rings** | OIG Special Fraud Alert on telefraud: patients recruited by telemarketers, little or no patient contact, pay correlated with "volume of federally reimbursable items", single product class (DME, genetic tests, diabetic supplies, creams) ([OIG SFA, Jul 2022](https://oig.hhs.gov/documents/root/1045/sfa-telefraud.pdf)) [VERIFIED] | Referral concentration (HHI = Herfindahl–Hirschman index). Reciprocal referrals. Dense communities with high internal referral share | referral edges | G, T |
| 15 | **Shared ownership / shell companies** | Providers must disclose owners with ≥5% stakes and managing employees, and update within 35 days of an ownership change ([CMS 455.104 toolkit](https://www.cms.gov/sites/default/files/repo-new/25/Toolkit%20for%20Disclosures%20of%20Ownership%20and%20Control%2042%20CFR%20455%20104%20_final.pdf)) [SUPPORTED]. Gold Rush used straw owners (row 8). DOJ 2026 describes data-driven targeting of "bust-out schemes" across 12 clinics (same release) [VERIFIED] | Entity resolution on owner, address, phone and bank token. Many NPIs at one suite. Owner linked to an excluded entity. Enroll → spike → vanish ("bust-out") | owner_id, address_norm, enroll/term dates | G, T |
| 16 | **Excluded providers** | Federal programs do not pay for items or services furnished, ordered or prescribed by excluded parties ([MLN](https://www.cms.gov/outreach-and-education/medicare-learning-network-mln/mlnproducts/downloads/fraud-abuse-mln4649244.pdf)) [VERIFIED]. States check the LEIE monthly ([455.436](https://www.ecfr.gov/current/title-42/chapter-IV/subchapter-C/part-455/subpart-E/section-455.436)) [VERIFIED] | Billing, rendering, ordering NPI or owner is in the LEIE with dos ≥ exclusion date | NPI, owner identity | R |
| 17 | **Evasion (adversarial)** | The 2026 hospice owner was "Concerned that Medicare and law enforcement used data analytics to monitor the percentage of patients discharged from hospice alive" and tried to game that metric ([DOJ 2026](https://www.justice.gov/opa/pr/national-health-care-fraud-takedown-results-455-defendants-charged-connection-over-65)) [VERIFIED] | **Single metrics get gamed. Combine independent signals** [INFERENCE] | — | multi |

---

## 4. Public reference data for rules

| Dataset | What it is | Format / fields | Licence and caveats |
|---|---|---|---|
| **Medicaid NCCI PTP + MUE files** | Quarterly complete files for practitioner, outpatient hospital and DME services. Q4 2026 is effective 1 Oct 2026. Medicaid has DME PTP edits ([CMS edit files](https://www.cms.gov/medicare/coding-billing/ncci-medicaid/medicaid-ncci-edit-files); [NCCI Medicaid](https://www.cms.gov/medicare/coding-billing/ncci-medicaid)) [VERIFIED] | ZIP containing TXT + XLSX. The practitioner and outpatient PTP files exceed Excel's 1,048,576-row limit. PTP columns: Column 1 code, Column 2 code, effective date, deletion date, modifier indicator (0 = not allowed, 1 = allowed, 9 = not applicable), rationale. MUE columns: code, MUE value, rationale. Approximate Q4 2026 sizes (my count): DME PTP ~45k rows, DME MUE ~2.8k, practitioner MUE ~15k [VERIFIED] | Each file states: "This file should NOT be used by state Medicaid programs as their edit file", because states get the official files through RISSNET. Each file also carries an AMA CPT copyright notice ("copyright 2025 American Medical Association") [VERIFIED]. **Demo use: take the HCPCS Level II rows plus synthetic pairs** [INFERENCE] |
| **OIG LEIE** | Active exclusions. The full file is replaced monthly, and reinstated parties are removed ([OIG downloads](https://oig.hhs.gov/exclusions/leie-database-supplement-downloads/)) [VERIFIED] | `UPDATED.csv` with header `LASTNAME,FIRSTNAME,MIDNAME,BUSNAME,GENERAL,SPECIALTY,UPIN,NPI,DOB,ADDRESS,CITY,STATE,ZIP,EXCLTYPE,EXCLDATE,REINDATE,WAIVERDATE,WVRSTATE`. My Oct 2026 download: 84,001 rows, **only 8,881 with a non-zero NPI**. Top exclusion types: 1128b4 (33,393), 1128a1 (26,047), 1128a2 (8,118) [VERIFIED] | Public, but contains no SSNs, so OIG says to confirm matches with its online search [VERIFIED]. Name-only matching gives false positives, and low NPI coverage means you must match on name + DOB + address [INFERENCE]. Use synthetic look-alike entries in the demo, not real names [INFERENCE] |
| **NPPES / NPI Registry** | All NPIs, with taxonomy (specialty) codes and practice locations | JSON API for lookups ([API](https://npiregistry.cms.hhs.gov/api-page)); monthly and weekly bulk files. Version 1 files were not supported after 3 Mar 2026 ([NPPES](https://download.cms.gov/nppes/NPI_Files.html)) [VERIFIED] | Real people. Use only taxonomy codes and formats, and generate synthetic NPIs. Real NPIs next to fraud scores could defame people [INFERENCE] |
| **CMS DE-SynPUF (2008–2010)** | Synthetic Medicare claims in five file types (beneficiary, inpatient, outpatient, carrier, Part D drug events). 20 samples linked by `DESYNPUF_ID`. 2008 sample totals: 2.33M beneficiaries and 34.3M carrier claims ([CMS](https://www.cms.gov/data-research/statistics-trends-and-reports/medicare-claims-synthetic-public-use-files/cms-2008-2010-data-entrepreneurs-synthetic-public-use-file-de-synpuf)) [VERIFIED] | CSV in ZIPs | CMS warns of "very limited inferential research value". **No fraud labels.** Old codes (ICD-9 era) [VERIFIED/INFERENCE]. Good for schema realism only |
| **Synthea** | MITRE's synthetic patient generator, Apache 2.0 licence ([LICENSE](https://github.com/synthetichealth/synthea/blob/master/LICENSE)) [VERIFIED] | Exports `Claims` and `Claims Transactions` CSVs and FHIR (Fast Healthcare Interoperability Resources) `ExplanationOfBenefit` records. Costs come from triangular distributions ([wiki](https://github.com/synthetichealth/synthea/wiki/Claims,-Payers,-and-Insurance)) [VERIFIED] | The wiki warns its CSV is not representative of real-world data repositories [VERIFIED]. It may lack billing-grade HCPCS lines [UNCERTAIN]. **It does produce claims, but you would have to add providers, referrals, ownership and fraud yourself** [INFERENCE] |
| **Medicare Physician & Other Practitioners, by Provider and Service** | Real aggregates by NPI × HCPCS × place of service (latest data year 2024). Fields include `Rndrng_NPI`, `Rndrng_Prvdr_Type`, `HCPCS_Cd`, `Place_Of_Srvc`, `Tot_Benes`, `Tot_Srvcs`, `Avg_Sbmtd_Chrg`, `Avg_Mdcr_Pymt_Amt` ([data.cms.gov](https://data.cms.gov/provider-summary-by-type-of-service/medicare-physician-other-practitioners/medicare-physician-other-practitioners-by-provider-and-service)) [VERIFIED] | CSV + API | Use it to calibrate realistic peer distributions, such as E/M level mix by specialty [INFERENCE]. It contains CPT descriptors, so don't redistribute them [INFERENCE] |
| **Kaggle "Healthcare Provider Fraud Detection Analysis"** (rohitrox) | Provider-level `PotentialFraud` labels plus inpatient, outpatient and beneficiary tables. Kaggle metadata lists the licence as CC0 ([Kaggle](https://www.kaggle.com/datasets/rohitrox/healthcare-provider-fraud-detection-analysis)) [VERIFIED] | CSV | **Provenance unknown.** Yoo et al. 2023 say the origin "cannot be accurately known". Their merged data had 212,232 of 556,703 rows (~38%) labelled fraud ([Yoo 2023](https://doi.org/10.1109/ACCESS.2023.3305962)) [VERIFIED]. About 9% of providers are positive ([Curtis 2025](https://link.springer.com/article/10.1186/s40537-025-01295-3)) [VERIFIED]. Use only as a sanity benchmark |
| **LEIE-labelled Medicare Part B/D** | The research standard: label providers by LEIE match. Highly imbalanced: Part B worse than 10,000:1; Part D 0.07% positive ([Curtis 2025](https://link.springer.com/article/10.1186/s40537-025-01295-3)) [VERIFIED] | Join | Exclusion is a noisy proxy for fraud, which the literature calls "class noise" (same source) [VERIFIED] |

**CPT licensing.** The AMA FAQ (updated 14 Jul 2026) says a licence is needed for any use, including development and testing. It prohibits training AI on the CPT Standard Data File and uploading CPT into public AI systems; retrieval-based AI is allowed under licence ([AMA](https://www.ama-assn.org/practice-management/cpt/cpt-licensing-frequently-asked-questions-faqs)) [VERIFIED]. Whether a student demo that shows a few code numbers needs a licence is **[UNCERTAIN]**.

**Recommendation [INFERENCE]:**
1. Use real **HCPCS Level II** codes for DME (A/E/K/L), ambulance (A04xx) and drugs (J).
2. Use **synthetic codes** for physician services (for example `EM-EST-1..5`, `PSY-30/45/60`, `LAB-GEN-01`), each tagged `code_system="SYNTH"`.
3. Ship no CPT descriptors.
4. Send no CPT content to a public LLM.

---

## 5. Detection methods and what is feasible in 1–2 weeks

### 5.1 What the literature says

- **Reviews.**
  - du Preez et al. (2025) reviewed 137 studies: 94 supervised, 41 unsupervised, 12 hybrid ([doi](https://doi.org/10.1016/j.artmed.2024.103061)) [SUPPORTED: abstract].
  - Curtis et al. (2025) reviewed 22 novel classifiers published Dec 2017–Oct 2024. Graph-based methods were the largest group (8 of 22). Only one work shared code. Reported F1 ranged from 0.15 to 0.948, and they found "few to no works which establish benchmarks" ([Curtis 2025](https://link.springer.com/article/10.1186/s40537-025-01295-3)) [VERIFIED].
  - Leevy et al. (2024) reviewed unsupervised methods such as Isolation Forest and autoencoders, and named gaps in interpretability, transfer and incremental learning, and benchmarking ([IEEE](https://ieeexplore.ieee.org/document/10729915); summarized in Curtis 2025) [VERIFIED secondary].
  - Joudaki et al. (2015) proposed a seven-step data-mining workflow for health fraud ([PMC](https://pmc.ncbi.nlm.nih.gov/articles/PMC4796421/)) [SUPPORTED].
  - Bauder, Khoshgoftaar & Seliya surveyed upcoding detection ([doi](https://doi.org/10.1007/s10742-016-0154-8)) [VERIFIED citation].
- **Same data, different results.** On the same Kaggle dataset, papers report F1 anywhere from 0.49 to 0.90 ([Curtis 2025](https://link.springer.com/article/10.1186/s40537-025-01295-3)) [VERIFIED]. **Takeaway [INFERENCE]:** no published model is a safe default. A carefully evaluated hybrid beats a fancy single model in front of judges.

### 5.2 Method families

1. **Rules and edits.** Deterministic, explainable and standard industry practice (RuleIT; CMS FPS prepayment edits). CMS FPS uses four model types: "rules-based, anomaly, predictive, and network" ([FPS 2nd-year report](https://www.cms.gov/About-CMS/Components/CPI/Widgets/Fraud_Prevention_System_2ndYear.pdf)) [VERIFIED]. That gives you a government-blessed rationale for a four-layer design.
2. **Peer-group anomaly detection.**
   - OIG's IQR fence ([OIG HH](https://oig.hhs.gov/documents/evaluation/2847/OEI-04-11-00240-Complete%20Report.pdf)) [VERIFIED].
   - Robust z-scores within specialty × region.
   - Isolation Forest ([Liu, Ting & Zhou 2008](https://doi.org/10.1109/ICDM.2008.17)) [VERIFIED citation].
   - Benford's law (leading-digit distribution) is only a screening aid, because payment rules can break its assumptions ([MDPI Healthcare 2025](https://www.mdpi.com/2227-9032/13/12/1464)) [SUPPORTED].
3. **Supervised ML on provider aggregates.** All of these use LEIE labels on Medicare data:
   - Logistic regression reached AUC 0.816 ([Herland et al. 2018](https://doi.org/10.1186/s40537-018-0138-3)) [SUPPORTED].
   - CatBoost reached AUC 0.785, rising to 0.890 when the provider's state was added ([Hancock & Khoshgoftaar, via Curtis 2025](https://link.springer.com/article/10.1186/s40537-025-01295-3)) [VERIFIED secondary]. That jump hints that geography is confounding the model [INFERENCE].

   Gradient-boosted trees (LightGBM or XGBoost) with class weights are the pragmatic choice [INFERENCE].
4. **Temporal analytics.** Change-points and CUSUM (cumulative-sum change detection) on monthly billing; "bust-out" velocity (DOJ 2026 cites data-driven bust-out targeting) [VERIFIED above]. Cost-sensitive learning on temporal trajectories reduced dollar losses on Part D ([Shi et al. 2023, via Curtis](https://link.springer.com/article/10.1186/s40537-025-01295-3)) [VERIFIED secondary].
5. **Graph analytics.**
   - **Centrality features, not GNNs.** Yoo, Shin & Kyeong built provider–beneficiary and provider–physician bipartite graphs and computed degree, eigenvector, closeness and PageRank centrality. ML with these features beat the best GNN (HAN) by about +4 percentage points precision, +24 recall and +14 F1. The GNN took roughly 250–300× longer to train ([IEEE Access 2023](https://doi.org/10.1109/ACCESS.2023.3305962)) [VERIFIED]. Caveat: this was on the Kaggle data, whose provenance is unknown.
   - **Shared locations.** Risk propagation across geospatially co-located providers predicted LEIE exclusion with F1 0.919 and AUC 0.960, mostly driven by collocation features ([Branting et al. 2016](https://doi.org/10.1109/ASONAM.2016.7752336)) [SUPPORTED: abstract].
   - **Community detection**: Louvain ([Blondel 2008](https://doi.org/10.1088/1742-5468/2008/10/P10008)) and Leiden, which guarantees well-connected communities ([Traag 2019](https://doi.org/10.1038/s41598-019-41695-z)) [VERIFIED citations].
   - **A deployed system**: a graph-based FWA system with a network-explorer interface ([Liu et al. 2016](https://doi.org/10.1609/aimag.v37i2.2630)) [SUPPORTED].
   - **GNN results are dataset-dependent**: F1 of about 0.87–0.90 on private Chinese insurance datasets, but 0.49–0.53 on Kaggle ([Curtis 2025](https://link.springer.com/article/10.1186/s40537-025-01295-3)) [VERIFIED]. **Do not build a GNN for the prototype** [INFERENCE].

### 5.3 Recommended prototype stack [INFERENCE]

| Layer | Tooling | Output the brief can cite |
|---|---|---|
| Rules (~15) | Python + DuckDB/SQL; rules in YAML (ID, text, severity, source URL) | `rule_hits(rule_id, claim_ids, evidence)` |
| Peer anomaly | pandas, scikit-learn `IsolationForest`, robust z | Top deviating metrics vs the peer median |
| Graph | NetworkX/igraph + `leidenalg`; personalized PageRank seeded from known-bad entities | Community, shared attributes, path to a known-bad entity |
| Supervised/temporal | LightGBM + [SHAP](https://shap.readthedocs.io/en/latest/) | Top-k reason codes |
| Fusion | Calibrated logistic stacker over layer scores | `p_fwa`, plus evidence strength = number of independent layers that agree |

---

## 6. 30/60/90-day risk prediction

### 6.1 Framing [INFERENCE]

- **Unit of prediction:** a provider-month (optionally a member-month) with snapshot date *t*.
- **Event:** the first of these in the window (*t*, *t+h*]:
  - a substantiated case outcome;
  - a new high-severity rule hit;
  - more than X% escalation in dollars on flagged codes.

  "Repeat" means a prior substantiated or education outcome. "Escalating" means the flagged metric is trending up.
- **Option A:** three separate per-horizon classifiers. Simple, but the risks can contradict each other (p30 > p60).
- **Option B (recommended): discrete-time hazard.** Expand the data to one row per entity per 30-day interval, then fit one classifier for *h_k* = P(event in interval *k* | no event before). Cumulative risk is `F(90) = 1 − (1−h1)(1−h2)(1−h3)`. Risks rise monotonically with the horizon, and censoring (entities that leave the data) is handled. Survival baselines: [lifelines](https://lifelines.readthedocs.io/en/latest/), [scikit-survival](https://scikit-survival.readthedocs.io/en/stable/).

### 6.2 Leakage traps

Leakage means using information that would not be available at prediction time ([Kaufman et al. 2012](https://doi.org/10.1145/2382577.2382579)) [VERIFIED citation]. Traps specific to this problem [INFERENCE]:
1. **Random splits.** Use rolling-origin time splits instead ([TimeSeriesSplit](https://scikit-learn.org/stable/modules/generated/sklearn.model_selection.TimeSeriesSplit.html)).
2. **Late claims.** Features must satisfy both `dos ≤ t` and `received_date ≤ t`.
3. **Label dating.** Date a label by when the finding was made (case closure), not by the service dates it covers.
4. **Process features** such as "records requested" or "payment suspended". They encode the label.
5. **Ring members split across train and test.** Use group splits by community or scheme.
6. **Generator artefacts**: scheme columns, ID ranges, round amounts.

### 6.3 Evaluation

- **PR-AUC** rather than ROC-AUC when classes are imbalanced ([Saito & Rehmsmeier 2015](https://doi.org/10.1371/journal.pone.0118432)) [VERIFIED citation].
- **Precision@k and recall@k**, where *k* = investigator capacity (for example 3 investigators × 4 new cases a week × 4 weeks = 48). Also **dollar-weighted recall**: the share of planted fraud dollars captured in the top *k* [INFERENCE].
- **Calibration**: reliability diagram and Brier score, then fix with Platt or isotonic scaling ([Niculescu-Mizil & Caruana 2005](https://doi.org/10.1145/1102351.1102430); [scikit-learn](https://scikit-learn.org/stable/modules/calibration.html)) [VERIFIED]. The queue multiplies p × dollars, so p must be calibrated [INFERENCE].
- **Break down results** by scheme, by held-out variant (§9) and by false-positive rate on hard negatives, with bootstrap confidence intervals [INFERENCE].

---

## 7. SIU queue prioritization

### 7.1 Borrow what CMS already does

- **Vulnerability scoring** (Medicare PIM ch. 4 §4.13), each factor scored 1–4 ([PIM ch. 4](https://www.cms.gov/Regulations-and-Guidance/Guidance/Manuals/Downloads/pim83c04.pdf)) [VERIFIED]:
  - **Likelihood**: 4 = ≥75%, 3 = 50–75%, 2 = 25–50%, 1 = <25%.
  - **Patient harm**: 4 = life-threatening, down to 1 = no harm.
  - **Financial impact**: 4 = ≥$200M, 3 = $100–200M, 2 = $10–100M, 1 = <$10M.
  - **Breadth**: 4 = national, 3 = regional, 2 = pocketed, 1 = isolated.

  The dollar bands are national-scale. Rescale them to your synthetic plan [INFERENCE].
- **Exposure**: count outlier codes only; $50k threshold; waived when fraud is suspected. **Harm first**: zero tolerance, with a 2-business-day notice ([PIM ch. 3](https://www.cms.gov/files/document/chapter-3-medicaid-investigations-audits.pdf)) [VERIFIED].

### 7.2 Scoring and allocation [INFERENCE]

For each case *i* (a provider, or a ring that groups its alerts):

| Term | Definition |
|---|---|
| `p_i` | Calibrated probability of substantiated FWA within horizon *h* |
| `D_i` | Paid dollars on **flagged lines only**, plus projected run-rate over *h*. Show the two separately |
| `r_i` | Expected recovery fraction (configurable) |
| `H_i` | Harm score, 1–4 on the CMS scale, × the number of members affected |
| `S_i` | Severity, 1–4: phantom billing, billing after death or by excluded providers ranks above coding error |
| `E_i` | Evidence strength, 0–1: independent layers agreeing, rule determinism, data completeness |
| `c_i` | Estimated investigator hours, by scheme type and case size |

- **Value:** `EV_i = p_i·r_i·D_i + λ·H_i`, where λ is a policy slider that converts harm into dollar units.
- **Allocation:** choose cases to maximize ΣEV subject to Σc ≤ capacity C (0/1 knapsack). Use exact DP or OR-Tools for small queues, or sort greedily by EV/c.
- **Overrides:**
  1. H = 4 always goes to the top.
  2. Low `E_i` goes to a "needs more data" lane.
  3. Exposure under $50k with no fraud indicator goes to "monitor / provider education".
- **Explain every rank** with a waterfall chart, for example: "0.62 (calibrated) × $184k flagged × 0.5 recovery + harm 3 × 41 members; ~30 investigator-hours." **Demo moment:** move the capacity or λ slider and watch the queue re-rank.

---

## 8. Explainable brief, responsible AI and the precedent loop

### 8.1 Explanation sources [INFERENCE]

- Rule reason codes, each with its regulation or source link and the claim IDs that triggered it.
- SHAP values ([Lundberg & Lee 2017](https://arxiv.org/abs/1705.07874)), translated through a feature dictionary. For example: "top-level visit share 71% vs specialty median 18%".
- Peer percentiles.
- Network facts and a small graph image.
- A timeline with change-points.

### 8.2 Grounded LLM brief [INFERENCE]

1. Build an evidence pack (JSON) containing case metadata, rule hits, SHAP reasons, peer stats, graph facts, timeline, matched precedents and data-quality notes.
2. The LLM writes the brief section by section and cites an ID after every factual sentence (`[claim:C123]`, `[rule:R07]`, `[precedent:P-0012]`).
3. A validator checks that every cited ID exists and every number appears in the pack. It bans the words "fraud", "guilty" and "intent", and checks the recommended action against an allow-list.
4. If validation fails twice, render a deterministic template brief instead.
5. Always show the calibrated confidence and a **Limitations** section: synthetic data, no medical records, plausible legitimate explanations, model version.

**Allowed actions (human decides):** monitor, education letter, records request or prepayment review, open investigation, or escalate to the manager for possible MFCU referral. **Never auto-suspend.** Suspension needs a state finding of a credible allegation of fraud and has good-cause exceptions ([42 CFR 455.23](https://www.ecfr.gov/current/title-42/chapter-IV/subchapter-C/part-455/subpart-A/section-455.23)) [VERIFIED].

### 8.3 Responsible-AI anchors

- **NIST AI RMF 1.0** has four functions: GOVERN, MAP, MEASURE, MANAGE ([NIST AI 100-1](https://nvlpubs.nist.gov/nistpubs/ai/NIST.AI.100-1.pdf)) [SUPPORTED]. The **GenAI Profile** lists confabulation as a risk ([NIST AI 600-1](https://nvlpubs.nist.gov/nistpubs/ai/NIST.AI.600-1.pdf)) [SUPPORTED].
- **OMB M-25-21** requires human oversight, fail-safes and appeal for "high-impact" federal AI ([OMB](https://www.whitehouse.gov/wp-content/uploads/2025/02/M-25-21-Accelerating-Federal-Use-of-AI-through-Innovation-Governance-and-Public-Trust.pdf)) [SUPPORTED]. It binds federal agencies, not state vendors, but it is a good design reference [INFERENCE].
- **CMS AI Playbook v4**: "CMS is already using AI to combat fraud, waste, and abuse, detect anomalies in provider data". It also stresses AI that augments the workforce rather than replacing it ([CMS](https://ai.cms.gov/CMS-AI-Playbook.pdf)) [VERIFIED].
- **HIPAA minimum necessary** (HIPAA = Health Insurance Portability and Accountability Act; [45 CFR 164.502(b)](https://www.law.cornell.edu/cfr/text/45/164.502), [164.514(d)](https://www.ecfr.gov/current/title-45/subtitle-A/subchapter-C/part-164/subpart-E/section-164.514)) [SUPPORTED]. Apply it even to synthetic data [INFERENCE]:
  - role-based masking: analysts see tokens, investigators see names;
  - no direct identifiers in the LLM evidence pack.
- **Due process** ([42 CFR 455.13](https://www.ecfr.gov/current/title-42/chapter-IV/subchapter-C/part-455/subpart-A)) [VERIFIED].

### 8.4 LLM-Wiki precedent loop [INFERENCE, pattern from Karpathy]

```
raw/        immutable: policy excerpts, OIG summaries, data dictionary, closed case JSON, rule YAML
wiki/       index.md (catalog), log.md (append-only "## [2026-10-20] case-close | CASE-0042 | substantiated")
            schemes/*.md  rules/*.md  precedents/P-*.md  entities/provider-<token>.md
AGENTS.md   schema: page templates, citation rules, approval rules
```

Karpathy's gist defines these layers and operations, including an append-only `log.md` with date-prefixed entries, and notes that "good answers can be filed back into the wiki" ([gist](https://gist.github.com/karpathy/442a6bf555914893e9891c11519de94f)) [VERIFIED]. Applied to SIU work:
- **Ingest.** After a manager approves a case outcome, the LLM drafts a precedent page: pattern fingerprint (rules fired, top features, graph motif), decision, rationale, dollars, and the decisive evidence. A human approves the page before it merges.
- **Query.** New briefs retrieve and cite the top 3 similar precedents.
- **Lint.** Flag contradictory precedents, rules with high false-positive rates, and stale policy pages.
- **Feedback.** Approved outcomes become versioned labels for retraining. Repeated patterns become **rule proposals** that need human approval.

**Audit log (cyber angle).**
- Append-only JSONL. Each record stores `prev_hash` and `hash = SHA-256(prev_hash ‖ record)`.
- Events logged: data load, model version, score, brief (with prompt hash), human decision, rule change.
- Ship a `verify_chain` command and an "audit chain intact" badge in the UI.
- Fields mirror the PIM ch. 3 case-file items ([PIM ch. 3](https://www.cms.gov/files/document/chapter-3-medicaid-investigations-audits.pdf)) [VERIFIED for the field list].

---

## 9. Synthetic data plan [INFERENCE unless cited]

**Why generate your own data.** No public, claim-level, labelled Medicaid fraud dataset with networks exists. The Kaggle set has unknown provenance and provider-level labels ([Yoo 2023](https://doi.org/10.1109/ACCESS.2023.3305962)) [VERIFIED]. There is precedent for the approach: Schrupp et al. (ICCS 2024) simulated inpatient claims and injected literature-derived fraud patterns into 3.07% of records, and published their code ([doi](https://doi.org/10.1007/978-3-031-63772-8_22), [code](https://github.com/mad-lab-fau/inpatient-claims-simulator)) [VERIFIED].

**Tables and sizes (laptop scale):**

| Table | Rows | Notes |
|---|---|---|
| members | 20,000 | dob, sex, county, jittered lat/lon, date of death (~1–2% die during the timeline), eligibility spans, planted duplicate identities |
| providers | ~1,000 | synthetic NPI, specialty/taxonomy, individual or organization, address_id, enroll/term dates, synthetic LEIE flag |
| locations | ~300 | normalized address, type (clinic, hospital, DME, lab, pharmacy, ambulance base), capacity |
| owners | ~400 | person or organization, ownership % (≥5% disclosed), linked NPIs |
| referrals | ~60k | ordering → rendering NPI, date |
| claim lines | 0.6–1M over 18 months | claim/line IDs, type, member, billing/rendering/ordering NPI, dos, received_date, code_system, code, modifiers, units, minutes, dx, charge, allowed, paid, place of service |
| rx fills | ~150k | synthetic drug class, days supply, qty, MME, prescriber, pharmacy |
| evv_visits | ~80k | aide, member, start/end, lat/lon |
| investigations | ~150 historical | subject, opened/closed, outcome (substantiated / unsubstantiated / education), recovered $, scheme tag |
| ground_truth | — | **kept outside the feature pipeline**: scheme_id, type, variant, entity/claim IDs, start/end |

**Legitimate baseline.**
- Poisson or negative-binomial visit rates by specialty, with a long-tailed distribution of provider sizes and seasonality.
- E/M mix calibrated to the public Medicare Physician & Other Practitioners file.
- Realistic noise: late claims, voids and replacements, address typos, and a few legitimate visits missing EVV.
- **Hard negatives**: high-acuity practices, rural sole providers, dialysis centres with heavy transport use, large groups sharing one address, and families sharing an address.

**Base rates.** True prevalence is unknown. Published datasets range from 0.07% positive (Part D) to about 38% (Kaggle claim rows) ([Curtis 2025](https://link.springer.com/article/10.1186/s40537-025-01295-3)) [VERIFIED]. Choose about **2–4% of providers** and **0.5–1.5% of claim lines** as configurable knobs, and **state in the data card that these are design choices, not estimates.**

**Planted schemes.**
- 10–12 scheme types from §3, plus 3 rings:
  - a telefraud ring: a recruiter address, two telehealth orderers, three DME/lab suppliers with a shared owner, about 300 members;
  - a behavioral-health / sober-home ring;
  - a shell cluster: 5 NPIs at one suite, one owner linked to an excluded entity.
- Each scheme gets a start date, a ramp and sometimes a stop (a bust-out).
- Some providers receive "education" and then escalate. This is what makes the 30/60/90 prediction meaningful.
- Add one **camouflaged** variant that keeps every single metric just under its threshold. It is inspired by the 2026 hospice case ([DOJ 2026](https://www.justice.gov/opa/pr/national-health-care-fraud-takedown-results-455-defendants-charged-connection-over-65)) [VERIFIED].

**Honest evaluation.** Give each scheme an A and a B variant, tune on A and test on B. Examples:
- +1 E/M level on every visit vs gradual drift;
- exact duplicates vs modifier-shifted duplicates;
- more than 24h a day vs 14–20h days that overlap inpatient stays;
- rings of 4 vs rings of 15 with sparse links.

Also hold out one whole scheme type, such as ambulance. Investigation labels should be partial (only 30–50% of bad providers were ever investigated) and noisy (some "unsubstantiated" cases are actually bad), mirroring the class noise described in the literature ([Curtis 2025](https://link.springer.com/article/10.1186/s40537-025-01295-3)) [VERIFIED concept].

**Pitfalls to avoid:**
- Planted fraud that is trivially detectable: round amounts, 10× spikes, sequential IDs, everything starting in one month.
- The same person writing both the generator and the detectors. Have a different teammate write the B variants after the detectors are frozen.
- Leaking ground-truth columns into features. Add a unit test that fails if any feature column comes from ground truth.
- Unreproducible data. Fix seeds, keep a YAML config, and publish a data card (sizes, rates, schemes, variants, limitations).

---

## 10. Differentiators and judge questions

### 10.1 Top recommendations [INFERENCE]

1. **One end-to-end journey in under 4 minutes.** Load data → dashboard funnel (alerts → cases → queue that fits capacity, with real counts) → case page (evidence, timeline, graph, brief) → human decision → audit log → precedent created.
2. **Honest evaluation table.** Precision@capacity, dollar-recall, PR-AUC and Brier score, reported per scheme, on held-out variants, and as the false-positive rate on hard negatives.
3. **Government-aligned language:**
   - the four FPS model types;
   - the CMS likelihood/harm/financial/breadth rubric;
   - the 45-day screening clock;
   - dollars at risk counted on outlier codes only;
   - a 455.23 good-cause warning badge (sole community provider).
4. **Acentra fit.** "Post-payment analytics and audit workflow (ClaimsSure/Audit Studio-style) feeding human-approved prepayment rule proposals (RuleIT-style), with source-backed briefs (Navigator-style)." Never claim to replicate their products.
5. **Responsible AI made visible:**
   - a "why ranked" waterfall;
   - a needs-more-data lane;
   - a citation-validator badge;
   - human approval gates;
   - role-based masking;
   - the hash-chained audit log.
6. **Code quality** (it is scored):
   - typed Python, ruff, mypy;
   - a pytest positive/negative fixture for every rule;
   - pandera or pydantic data contracts;
   - seeds;
   - `make data / train / eval / demo`;
   - CI;
   - ADRs (architecture decision records);
   - an architecture diagram.
7. **Licensing hygiene.** No CPT descriptors, synthetic NPIs, no real LEIE or NPPES names.

### 10.2 Likely judge questions

| Question | Sourced answer |
|---|---|
| Is the 6.12% improper payment rate fraud? | No. CMS says it "is not a measure of fraud", and 77.17% was documentation issues ([CMS](https://www.cms.gov/newsroom/fact-sheets/fiscal-year-2025-improper-payments-fact-sheet)) [VERIFIED] |
| Why rules *and* ML? | CMS FPS combines rules-based, anomaly, predictive and network models ([FPS](https://www.cms.gov/About-CMS/Components/CPI/Widgets/Fraud_Prevention_System_2ndYear.pdf)) [VERIFIED] |
| Why no GNN? | Centrality features in ML beat the best GNN on recall and F1 and trained far faster ([Yoo 2023](https://doi.org/10.1109/ACCESS.2023.3305962)) [VERIFIED], and they are easier to explain [INFERENCE] |
| Is your accuracy inflated? | We use temporal and ring-grouped splits, held-out variants, hard negatives and calibration. The field has almost no benchmarks: F1 0.15–0.948 ([Curtis 2025](https://link.springer.com/article/10.1186/s40537-025-01295-3)) [VERIFIED] |
| What happens to an innocent provider who gets flagged? | Only human-review actions are available. Due process is required ([455.13](https://www.ecfr.gov/current/title-42/chapter-IV/subchapter-C/part-455/subpart-A)). Suspension needs a credible allegation and has good-cause exceptions ([455.23](https://www.ecfr.gov/current/title-42/chapter-IV/subchapter-C/part-455/subpart-A/section-455.23)) [VERIFIED] |
| How do you count dollars and capacity? | Flagged codes only, with a $50k exposure guide ([PIM ch. 3](https://www.cms.gov/files/document/chapter-3-medicaid-investigations-audits.pdf)). Capacity is a parameter, consistent with NY's "optimal caseload per investigator" ([NY DFS](https://www.dfs.ny.gov/system/files/documents/2022/11/ffp_guidelines_20221115.pdf)) [VERIFIED] |
| How do you stop LLM hallucination? | Evidence-pack grounding, an ID and number validator, and a template fallback, which addresses NIST's confabulation risk ([NIST 600-1](https://nvlpubs.nist.gov/nistpubs/ai/NIST.AI.600-1.pdf)) [SUPPORTED] |
| Can you use CPT? | Not without a licence ([AMA](https://www.ama-assn.org/practice-management/cpt/cpt-licensing-frequently-asked-questions-faqs)) [VERIFIED]. We use HCPCS Level II plus synthetic codes |
| Why network analysis? | Gold Rush used straw owners across dozens of DME firms ([DOJ 2025](https://www.justice.gov/opa/pr/national-health-care-fraud-takedown-results-324-defendants-charged-connection-over-146)) [VERIFIED]. Shared-location propagation predicts exclusion ([Branting 2016](https://doi.org/10.1109/ASONAM.2016.7752336)) [SUPPORTED] |
| Does it work for managed care? | Yes, on encounter data. The PERM managed-care rate does not review plan payments to providers ([GAO-25-107770](https://www.gao.gov/products/gao-25-107770)) [SUPPORTED]. MFCUs received 5,991 referrals from managed care entities in FY2025 ([OIG](https://oig.hhs.gov/reports/all/2026/medicaid-fraud-control-units-annual-report-fiscal-year-2025/)) [VERIFIED] |
| How does it learn? | Approved outcomes become precedents, labels and rule proposals, all logged, following the LLM-Wiki pattern ([Karpathy](https://gist.github.com/karpathy/442a6bf555914893e9891c11519de94f)) [VERIFIED pattern] |

---

## 11. Unverified / open questions

1. **ClaimsSure internals**, including the "four factors" named on the Utah course page; also Audit Studio features beyond public summaries.
2. **Navigator and the Acentra PI module.** Whether Navigator uses an LLM or RAG; what the PI module's models actually are.
3. **FEI Systems.** Whether it brings any program-integrity analytics (its press release names none).
4. **GAO-25-107770.** The finding is known from GAO's page summary and search results only; the PDF could not be fetched.
5. **OMB M-25-21, NIST AI RMF and NIST AI 600-1.** Details come from summaries; I did not read the full PDFs.
6. **SIU caseload benchmarks.** None verified, so none are given.
7. **Real-world fraud prevalence.** No authoritative claim-level figure exists. NHCAA's 3–10% is an estimate of losses.
8. **Kaggle dataset.** Origin and labelling method unknown.
9. **CPT in a non-commercial student demo.** No academic or hackathon exemption found.
10. **Synthea's billing-code fidelity** (whether it produces billing-grade HCPCS lines): not checked in code.
11. **Supporting details:** the MedCity 2017 author's affiliation; *U.S. v. Krizek* specifics; OIG Part D pharmacy measures (search summary only); the Benford limitations paper (MDPI blocked direct fetch).
12. **Hackathon rubric** beyond "code quality is scored", and whether Acentra will provide any data.

---

## 12. References

All URLs were accessed 6–8 Oct 2026. Inline links above point to the same sources.

**Regulations and CMS manuals:** [42 CFR 455 Subpart A](https://www.ecfr.gov/current/title-42/chapter-IV/subchapter-C/part-455/subpart-A) · [42 CFR 455.23](https://www.ecfr.gov/current/title-42/chapter-IV/subchapter-C/part-455/subpart-A/section-455.23) · [42 CFR 455.436](https://www.ecfr.gov/current/title-42/chapter-IV/subchapter-C/part-455/subpart-E/section-455.436) · [42 CFR 438.608](https://www.ecfr.gov/current/title-42/chapter-IV/subchapter-C/part-438/subpart-H/section-438.608) · [455.104 toolkit](https://www.cms.gov/sites/default/files/repo-new/25/Toolkit%20for%20Disclosures%20of%20Ownership%20and%20Control%2042%20CFR%20455%20104%20_final.pdf) · [Medicaid PIM ch. 3 (Rev. 13945)](https://www.cms.gov/files/document/chapter-3-medicaid-investigations-audits.pdf) · [Medicare PIM ch. 4 (Rev. 13879)](https://www.cms.gov/Regulations-and-Guidance/Guidance/Manuals/Downloads/pim83c04.pdf) · [Managed Care Fraud Referral Toolkit](https://www.cms.gov/files/document/managed-care-fraud-referral-toolkit.pdf) · [Medicaid RAC FAQ](https://www.cms.gov/medicare-medicaid-coordination/fraud-prevention/medicaidintegrityprogram/downloads/medicaid_rac_faq.pdf) · [MLN4649244](https://www.cms.gov/outreach-and-education/medicare-learning-network-mln/mlnproducts/downloads/fraud-abuse-mln4649244.pdf) · [Medicaid EVV](https://www.medicaid.gov/medicaid/home-community-based-services/guidance/electronic-visit-verification-evv) · [45 CFR 164.502](https://www.law.cornell.edu/cfr/text/45/164.502) · [45 CFR 164.514](https://www.ecfr.gov/current/title-45/subtitle-A/subchapter-C/part-164/subpart-E/section-164.514) · [NAIC Model 680](https://content.naic.org/sites/default/files/model-law-680.pdf) · [NY DFS SIU guidelines](https://www.dfs.ny.gov/system/files/documents/2022/11/ffp_guidelines_20221115.pdf)

**Statistics and enforcement:** [CMS FY2025 improper payments](https://www.cms.gov/newsroom/fact-sheets/fiscal-year-2025-improper-payments-fact-sheet) · [2025 PERM rates](https://www.cms.gov/files/document/2025-perm-medicaid-improper-payment-rates.pdf) · [GAO-25-107770](https://www.gao.gov/products/gao-25-107770) · [NHCAA](https://www.nhcaa.org/tools-insights/about-health-care-fraud/the-challenge-of-health-care-fraud/) · [OIG MFCU FY2025](https://oig.hhs.gov/reports/all/2026/medicaid-fraud-control-units-annual-report-fiscal-year-2025/) · [OIG MFCU overview](https://oig.hhs.gov/fraud/medicaid-fraud-control-units-mfcu/) · [DOJ 2025 Takedown](https://www.justice.gov/opa/pr/national-health-care-fraud-takedown-results-324-defendants-charged-connection-over-146) · [DOJ 2026 Takedown](https://www.justice.gov/opa/pr/national-health-care-fraud-takedown-results-455-defendants-charged-connection-over-65) · [CMS FPS 2nd-year report](https://www.cms.gov/About-CMS/Components/CPI/Widgets/Fraud_Prevention_System_2ndYear.pdf) · [FPS2 leaflet](https://www.cms.gov/files/document/dasg-leaflet-fps2.pdf)

**OIG and other scheme evidence:** [E/M OEI-04-10-00180](https://oig.hhs.gov/oei/reports/oei-04-10-00180.pdf) · [Home health OEI-04-11-00240](https://oig.hhs.gov/documents/evaluation/2847/OEI-04-11-00240-Complete%20Report.pdf) · [Ambulance OEI-09-12-00351](https://oig.hhs.gov/oei/reports/oei-09-12-00351.pdf) · [Opioids OEI-02-17-00250](https://www.oig.hhs.gov/oei/reports/oei-02-17-00250.pdf) · [Genetic testing alert](https://www.oig.hhs.gov/fraud/consumer-alerts/fraud-alert-genetic-testing-scam/) · [Telefraud SFA](https://oig.hhs.gov/documents/root/1045/sfa-telefraud.pdf) · [Capitation after death 2023](https://oig.hhs.gov/reports/all/2023/multiple-states-made-medicaid-capitation-payments-to-managed-care-organizations-after-enrollees-deaths/) · [NH duplicates](https://oig.hhs.gov/documents/audit/3432/A-01-04-00003-Complete%20Report.pdf) · [NY multiple IDs](https://oig.hhs.gov/documents/audit/6451/A-02-18-01020-Report%20in%20Brief.pdf) · [ABA Indiana](https://oig.hhs.gov/reports/all/2024/indiana-made-at-least-56-million-in-improper-fee-for-service-medicaid-payments-for-applied-behavior-analysis-provided-to-children-diagnosed-with-autism/) · [ABA Wisconsin](https://oig.hhs.gov/reports/all/2025/wisconsin-made-at-least-185-million-in-improper-fee-for-service-medicaid-payments-for-applied-behavior-analysis-provided-to-children-diagnosed-with-autism/) · [MACPAC lock-in](https://www.macpac.gov/wp-content/uploads/2019/08/Pharmacy-and-Provider-Lock-in-Programs-in-Medicaid-Fee-for-Service.pdf) · [U.S. v. Krizek](https://law.justia.com/cases/federal/appellate-courts/F3/192/1024/594113/)

**Data and coding:** [Medicaid NCCI edit files](https://www.cms.gov/medicare/coding-billing/ncci-medicaid/medicaid-ncci-edit-files) · [NCCI for Medicaid](https://www.cms.gov/medicare/coding-billing/ncci-medicaid) · [OIG LEIE](https://oig.hhs.gov/exclusions/leie-database-supplement-downloads/) · [NPPES files](https://download.cms.gov/nppes/NPI_Files.html) · [NPI API](https://npiregistry.cms.hhs.gov/api-page) · [DE-SynPUF](https://www.cms.gov/data-research/statistics-trends-and-reports/medicare-claims-synthetic-public-use-files/cms-2008-2010-data-entrepreneurs-synthetic-public-use-file-de-synpuf) · [Synthea licence](https://github.com/synthetichealth/synthea/blob/master/LICENSE) · [Synthea claims wiki](https://github.com/synthetichealth/synthea/wiki/Claims,-Payers,-and-Insurance) · [Medicare Physician & Other Practitioners](https://data.cms.gov/provider-summary-by-type-of-service/medicare-physician-other-practitioners/medicare-physician-other-practitioners-by-provider-and-service) · [Kaggle provider fraud](https://www.kaggle.com/datasets/rohitrox/healthcare-provider-fraud-detection-analysis) · [HCPCS readme](https://www.cms.gov/files/document/2020-hcpcs-alpha-numeric-hcpcs-readme-file.txt) · [HCPCS quarterly update](https://www.cms.gov/medicare/coding-billing/healthcare-common-procedure-system/quarterly-update) · [AMA CPT licensing FAQ](https://www.ama-assn.org/practice-management/cpt/cpt-licensing-frequently-asked-questions-faqs)

**Acentra:** [About](https://acentra.com/about-us) · [Solutions](https://acentra.com/solutions) · [eCAMS HCE / RuleIT](https://acentra.com/technologies/ecams-hce) · [Utah blog](https://acentra.com/blog/beyond-certification-how-utah-and-acentra-health-are-redefining-trust-and-accountability-in-medicaid-modernization) · [Utah PRISM news](https://acentra.com/news/acentra-health-implements-modular-cloud-based-medicaid-claims-system-for-utah/) · [Medicaid.gov pledges](https://www.medicaid.gov/resources-for-states/working-families-tax-cut-legislation/community-engagement/pledges-from-medicaid-tech-companies) · [Utah PRISM](https://medicaid.utah.gov/prism/) · [ClaimsSure course](https://medicaid.utah.gov/document/introduction-to-claimssure/) · [NAMPI 2025](https://acentra.com/events/national-association-for-medicaid-program-integrity-nampi-2025) · [FEI acquisition](https://acentra.com/news/acentra-health-acquires-fei-systems) · [MedCity News 2017](https://medcitynews.com/2017/02/predictive-analytics-can-tackle-opioid-crisis/)

**Literature:**
- Curtis, Billion-Polak, Khoshgoftaar & Furht, *J Big Data* 2025, [link](https://link.springer.com/article/10.1186/s40537-025-01295-3)
- du Preez et al., *AIIM* 2025, [doi](https://doi.org/10.1016/j.artmed.2024.103061)
- Leevy et al., IEEE BigDataService 2024, [link](https://ieeexplore.ieee.org/document/10729915)
- Joudaki et al. 2015, [PMC](https://pmc.ncbi.nlm.nih.gov/articles/PMC4796421/)
- Bauder et al. 2017, [doi](https://doi.org/10.1007/s10742-016-0154-8)
- Herland et al. 2018, [doi](https://doi.org/10.1186/s40537-018-0138-3)
- Johnson & Khoshgoftaar 2019, [doi](https://doi.org/10.1186/s40537-019-0225-0)
- Yoo, Shin & Kyeong 2023, [doi](https://doi.org/10.1109/ACCESS.2023.3305962)
- Branting et al. 2016, [doi](https://doi.org/10.1109/ASONAM.2016.7752336)
- Liu et al. 2016, [doi](https://doi.org/10.1609/aimag.v37i2.2630)
- Schrupp et al. 2024, [doi](https://doi.org/10.1007/978-3-031-63772-8_22)
- Liu, Ting & Zhou 2008, [doi](https://doi.org/10.1109/ICDM.2008.17)
- Blondel et al. 2008, [doi](https://doi.org/10.1088/1742-5468/2008/10/P10008)
- Traag et al. 2019, [doi](https://doi.org/10.1038/s41598-019-41695-z)
- Lundberg & Lee 2017, [arXiv](https://arxiv.org/abs/1705.07874)
- Saito & Rehmsmeier 2015, [doi](https://doi.org/10.1371/journal.pone.0118432)
- Kaufman et al. 2012, [doi](https://doi.org/10.1145/2382577.2382579)
- Niculescu-Mizil & Caruana 2005, [doi](https://doi.org/10.1145/1102351.1102430)
- Benford in healthcare, [MDPI](https://www.mdpi.com/2227-9032/13/12/1464)

**Responsible AI and tools:** [NIST AI 100-1](https://nvlpubs.nist.gov/nistpubs/ai/NIST.AI.100-1.pdf) · [NIST AI 600-1](https://nvlpubs.nist.gov/nistpubs/ai/NIST.AI.600-1.pdf) · [OMB M-25-21](https://www.whitehouse.gov/wp-content/uploads/2025/02/M-25-21-Accelerating-Federal-Use-of-AI-through-Innovation-Governance-and-Public-Trust.pdf) · [CMS AI Playbook v4](https://ai.cms.gov/CMS-AI-Playbook.pdf) · [Karpathy LLM Wiki](https://gist.github.com/karpathy/442a6bf555914893e9891c11519de94f) · [scikit-learn calibration](https://scikit-learn.org/stable/modules/calibration.html) · [TimeSeriesSplit](https://scikit-learn.org/stable/modules/generated/sklearn.model_selection.TimeSeriesSplit.html) · [lifelines](https://lifelines.readthedocs.io/en/latest/) · [scikit-survival](https://scikit-survival.readthedocs.io/en/stable/) · [SHAP](https://shap.readthedocs.io/en/latest/) · [NetworkX Louvain](https://networkx.org/documentation/stable/reference/algorithms/generated/networkx.algorithms.community.louvain.louvain_communities.html)
