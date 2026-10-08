# ClaimShield Nexus — research basis

Sources used for the synthetic generator, rule kinds, and SIU product shape.
Facts that were checked against a primary page or paper are marked **[VERIFIED]**.
Product inferences are marked **[INFERENCE]**.

## Why a synthetic labelled extract

No public, claim-level, labelled Medicaid fraud dataset with provider networks exists.
The Kaggle “Healthcare Provider Fraud Detection Analysis” set has unknown provenance and provider-level labels (Yoo et al. 2023, IEEE Access, https://doi.org/10.1109/ACCESS.2023.3305962) **[VERIFIED]**.
On that same Kaggle file, published F1 scores range from about 0.49 to 0.90, and GNN results collapse off private Chinese data onto Kaggle (Curtis et al. 2025, *Journal of Big Data*, https://doi.org/10.1186/s40537-025-01295-3) **[VERIFIED]**.

Precedent for injecting literature-derived schemes into simulated claims:
Schrupp, Klede, Raab, Eskofier (ICCS 2024), “Simulation and Detection of Healthcare Fraud in German Inpatient Claims Data”, https://doi.org/10.1007/978-3-031-63772-8_22, code https://github.com/mad-lab-fau/inpatient-claims-simulator **[VERIFIED]**.
They inject ~3% fraudulent records (ventilation-hour inflation, C-section swap, newborn weight, personal-care add-on, early “bloody” discharge, ICD-order swap). Gradient boosting / random forest ~80% weighted F1 on the simulator; they excel at compensation-related DRG upcoding.

Li, Huang, Ayvaci, Setia (M&SOM / related IS literature) and the CMS Fraud Prevention System design motivate **four layers**: rules, anomaly, predictive, network — alerts as leads, humans as the decision. CMS/GAO: analytics generate leads; CMS does not deny a claim solely from a model (GAO-26-107799) **[VERIFIED]**.

## Scheme → source map

| ID | Scheme | Primary sources |
| --- | --- | --- |
| S01 | Duplicate billing | OIG nursing-home duplicates A-01-04-00003; NCCI |
| S02 | E/M upcoding | OIG OEI-04-10-00180 |
| S03 | Panel unbundling | CMS Medicaid NCCI PTP files |
| S04 | Excess units / MUE | CMS MUE / MAI 3 same-day split |
| S05 | Billing after death | OIG capitation-after-death 2023; DME phantom supplies |
| S06 | Ambulance overlap / mileage (held-out type) | OIG OEI-09-12-00351 |
| S07 | Impossible BH hours | *United States v. Krizek*; DOJ health-care fraud takedowns |
| S08 | ABA during inpatient | OIG Indiana / Wisconsin ABA audits |
| S09 | Home health without EVV | 21st Century Cures EVV; MFCU FY2025 personal-care lead |
| S10 | Home health utilization fence | OIG OEI-04-11-00240 |
| S11 | Excluded-party billing | OIG LEIE |
| S12 | Doctor shopping | OIG OEI-02-17-00250 |
| G1 | Telefraud / catheter mill | OIG telefraud SFA 2022; GAO catheter scheme 2023–24 |
| G2 | Sober-home / recruiter ring | DOJ 2025 national takedown (~$650M SUD Arizona) |
| G3 | Shell cluster / straw owners | 42 CFR 455.104; Gold Rush straw owners |
| C1 | Camouflage just under thresholds | DOJ 2026 hospice metric gaming |
| S13 | Place-of-service mismatch | CMS POS policy; common FWA edit |
| S14 | Sex-implausible procedure | NCCI medically unlikely / demographic edits |
| S15 | Weekend mill | Peer-anomaly literature; office-only specialties |
| S16 | Mileage padding | OIG ambulance OEI-09-12-00351 |
| S17 | Referral monopoly (HHI) | Kickback / Stark pattern; graph layer |
| S18 | Clone billing | Identical charges across members same day |
| S19 | Stay compression | Schrupp 2024 “bloody release” analogue |
| S20 | Diagnosis-order swap | Schrupp 2024 ICD-order analogue |
| S21 | Genetic-testing mill | OIG genetic-testing consumer alert |
| HN1/HN2 | Hard negatives | High-volume legitimate E/M; allowed PTP indicator 1 |

## Methods papers (product, not just models)

- Bauder & Khoshgoftaar — Medicare fraud class imbalance; rare-event framing.
- van Capelleveen et al. — outlier-based healthcare fraud, peer comparison.
- Joudaki et al. / Li et al. 2008 survey — statistical FWA methods taxonomy.
- CMS FPS — risk scores on providers, leads to UPICs, not auto-denial.
- Discrete-time hazard (Allison; Jenkins) — 30/60/90 confirmation risk on open cases **[INFERENCE for this product]**.
- Knapsack / capacity-aware ranking — SIU hours are the scarce resource **[INFERENCE]**.

## Public files we emulate, never redistribute as CPT

- Medicaid NCCI PTP and MUE edit *logic* (our own SYNTH/HCPCS2 tables).
- OIG LEIE format (synthetic NPIs, Luhn checksum, no real excluded persons).
- HCPCS Level II ambulance codes A0425 / A0427 only (not AMA CPT).
- CMS POS codes 11/12/21/23/41.

## Evaluation contract (honest, not leaderboard)

Report precision@capacity, dollar-recall, per-scheme recall on **B variants**, recall on **held-out S06**, and false-positive rate on **HN1/HN2**.
Never train on `ground_truth.csv`. A unit test fails if scheme columns leak into claim/feature tables.

## Licences (proposed)

Generator code and policy notes: MIT.
Generated tables: CC0 with this data card.
Do not ship AMA CPT descriptors.
