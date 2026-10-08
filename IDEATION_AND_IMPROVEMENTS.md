# ClaimShield Nexus: Ideation and What We Improved

Author: IDEA LAB (product strategy). Planning document, no code. Facts about Acentra's
products and public CMS/OIG material should be re-verified against Research Lab's brief
before they go into the deck.

## 1. Who the user is and what the problem is

**Primary user:** the Special Investigations Unit (SIU) investigator at a payer or Medicaid
program-integrity team. **Second user:** the SIU manager, who owns team capacity and the
queue. **Supporting users:** the policy analyst (writes rules) and the auditor (read-only
oversight).

**Problem:** an investigator faces thousands of unconnected alerts but can open only a
small number of cases a week. Two things go wrong at once:

1. Money is lost on the fraud nobody reached, because alerts are ranked by score and not
   by what a limited team can actually work.
2. Honest providers are disrupted by cases that should never have been opened. The PS
   names both costs ("member harm", "provider disruption"), so we measure both.

**Product promise:** turn thousands of unexplained alerts into a short, ranked set of
evidence-backed cases that fits the team's hours, and get measurably better every time an
investigator closes a case.

## 2. User journey (what the user enters, what the system does, what comes back)

| Step | User does | System does | User gets back |
|---|---|---|---|
| 1 | Manager loads a claims batch (synthetic CSV, X12 837 or FHIR Claim) | Validates against the core schema | Data-quality report: rows loaded, rejected, and why |
| 2 | Manager sets team hours this week and the 30/60/90-day horizon | Runs rules, peer anomaly scoring, graph analytics, temporal model; groups related alerts into cases | "N alerts became M cases" |
| 3 | Investigator opens the queue | Selects the case set with the highest expected value inside the hours budget | Ranked queue with the six PS factors shown per case |
| 4 | Investigator opens a case | Builds a brief only from computed evidence; every sentence cites a claim row, rule, or precedent | Brief: evidence, timeline, network, confidence, limitations, recommended action |
| 5 | Investigator decides: escalate, monitor, or dismiss, with a reason | Writes an append-only audit entry; stores the decision as a label and precedent; updates the provider's wiki page | Next run re-ranks using the new outcome |
| 6 | System is unsure | Routes to a "needs more evidence" lane, lists the data that would settle it | Never auto-labels fraud |

## 3. Core features (map 1:1 to the PS)

- Ingest and schema validation for claims, providers, members, facilities, referrals,
  ownership links, and past investigations.
- Claim-level detection: duplicates, upcoding (peer comparison), unbundling and unit caps
  (our own edit tables in CMS's NCCI/MUE format; no AMA files in the repo), phantom
  services, excessive utilization, impossible timing.
- At least two complementary approaches: rules + ML anomaly scoring + graph + temporal,
  reported separately and combined.
- Relationship graph with a two-hop neighbourhood view.
- 30/60/90-day repeat or escalation risk, backtested on a time split with calibration.
- Capacity-aware SIU queue ranked by risk, dollars, member impact, severity, evidence
  strength, and capacity.
- Explainable, cited investigation brief with a recommended human-review action.

## 4. Extra features beyond the PS (our ideas)

Each one is small enough to build in the hackathon and answers something an SIU team
actually struggles with.

1. **Alert-to-case consolidation.** Related alerts (shared provider, owner, address,
   referral chain) are merged into one case. Headline metric: compression ratio.
2. **Capacity-aware selection, not sorting.** The queue solves a small knapsack problem:
   maximize expected recoverable dollars, weighted by member harm and evidence strength,
   within the manager's hours.
3. **The loop that gets smarter, measured.** Every decision becomes a label and a
   precedent. We plot top-25 hit rate against number of decided cases.
4. **Scheme displacement watch.** When a rule goes live, fraudsters often shift billing to
   a neighbouring code or a different provider in the same ring. After each rule change we
   compare code mix before and after for flagged providers and raise a "possible
   displacement" alert. Most teams treat rules as static; this treats fraud as adaptive.
5. **Statistical sampling and overpayment estimate.** Investigators rarely review every
   claim; they sample and extrapolate. The case page draws a reproducible random sample
   of claims for a records request and shows an overpayment estimate with a confidence
   interval, in the spirit of OIG's RAT-STATS sampling tool.
6. **Action ladder for the recommendation.** The recommended human-review action uses real
   program-integrity steps in increasing severity: provider education letter, medical
   records request, prepayment review, referral to the state Medicaid Fraud Control Unit,
   and payment suspension on a credible allegation of fraud (42 CFR 455.23), which is the
   state's decision. The system recommends; a human decides.
7. **Entity resolution.** The same actor billing under different NPIs, addresses, phone
   numbers, or bank accounts is linked before graph analysis, so rings can't hide behind
   new identifiers.
8. **Fairness guard on peer comparison.** Providers are compared within specialty, region,
   and patient case-mix, so rural or high-need practices aren't flagged just for serving
   sicker members. Flag rates by peer group are shown on the outcomes page.
9. **Grounding check on every brief.** Each generated sentence is checked against the
   evidence IDs it cites; unsupported sentences are dropped and counted. Metric: citation
   coverage of 100% on shipped briefs.
10. **"Why this case ranks above that one."** A side-by-side explanation of two queue
    items, factor by factor, so managers can defend prioritization.
11. **Referral packet export.** One click produces a case packet (brief, evidence table,
    sample, timeline, audit trail) for escalation.
12. **Rules as versioned data linked to policy text,** testable on last month's claims
    before going live, in the spirit of Acentra's RuleIT.

## 5. What we improved over the usual approach

| Usual hackathon approach | ClaimShield Nexus | Why it matters to an SIU |
|---|---|---|
| Score each claim, show a list of alerts | Merge alerts into cases around entities and networks | Investigators work cases, not rows |
| Sort by risk score | Select within team capacity by expected value | A 20-case week needs the best 20, not the top 20 scores |
| Static model | Investigator outcomes feed labels and precedent; improvement is plotted | Value compounds, as the masterclass asked |
| Static rules | Versioned rules, pre-launch test, displacement watch | Fraud adapts to rules |
| LLM chatbot over the data | LLM writes only from computed evidence, every sentence cited and checked | Defensible in a referral |
| Accuracy on the same synthetic data it was trained on | Time split, unseen scheme variants, rules vs ML vs combined | Honest numbers judges can trust |
| Dollars caught only | Dollars caught plus false positives in top K and member impact | Counts provider disruption and member harm |
| Replaces the payer's system | Sits downstream of eCAMS-style claims systems via X12/FHIR adapters and feeds program integrity | Something Acentra could actually adopt |

## 6. Measurable outcomes we will report (all on synthetic data, labelled as such)

- Alert-to-case compression ratio.
- Precision in the top K cases and false positives in the top K.
- Recall per planted scheme, including variants unseen in training.
- Rules-only vs ML-only vs combined recall.
- Expected dollars recovered per investigator-hour at the chosen capacity.
- Calibration of the 30/60/90-day risk on a time-split backtest.
- Top-25 hit rate as decided cases accumulate.
- Citation coverage of generated briefs.

## 7. Scope guardrails

- Out: graph neural networks, Neo4j, Kafka, any real patient or provider data, AMA CPT files.
- In the MVP: 10 to 12 planted schemes across service lines (extra weight on home health and
  behavioral health), 3 fraud rings including one cross-line referral ring, legitimate but
  unusual providers as hard negatives, one scheme type held out entirely for testing, and
  one full loop (load, rank, brief, decide, re-rank) shown end to end.
- Possible patient harm always goes to the top of the queue, whatever the dollar value.
- Never present Medicaid improper-payment figures as fraud figures; CMS says they are not a
  measure of fraud (see Research Lab's brief).
- Stretch, only if the MVP is done: displacement watch, sampling estimate, packet export.
