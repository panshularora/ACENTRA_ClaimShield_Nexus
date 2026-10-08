# ClaimShield Nexus risk models: model card

Two models score every case the pipeline builds:

- **P(confirm)**: the probability that investigating the case finds a planted scheme.
- **30/60/90-day risk**: the probability that the case's riskiest provider bills a planted fraudulent claim line within 30, 60 or 90 days after the data cutoff.

Both models are trained and backtested on **synthetic data only**. They rank and prioritise the queue. They are not evidence of fraud, and they never change a claim, a payment or a case decision. Investigators decide what to work.

Artifact: `data/models/risk_model.json`, version `risk-d9b7d941c214`, training-data hash `866ba87e1f196038`.
Rebuild: `cd backend && make train`, or `uv run python -m claimshield train --profile panel --seed 7`.
Live summary and metrics: `GET /api/v1/models/risk` (requires `model:read`).
Code: `backend/src/claimshield/risk/`.

## Labels

Labels are read only from generator ground truth (`risk/labels.py`). Ground truth never enters a feature table.

**Hazard event.** For provider *p* and cutoff *t*, the event is the first service date after *t* of a planted fraudulent claim line (`is_fraud` ground-truth rows) billed by *p*. Monthly interval *k* covers (t + 30(k−1), t + 30k] days, and risk at *h* days is P(event in (t, t + h]). Hard negatives (`is_fraud = False`) never create events. A window that runs past the end of the data is censored: it is left out rather than labelled 0.

**Case confirmation.** A case built at cutoff *t* is labelled 1 when any of these holds:

- one of its flagged lines is a planted fraudulent line;
- one of its provider subjects billed planted fraudulent lines with service dates on or before *t*;
- for schemes planted as links rather than lines (rings G1–G3, shell S12, referral S17), a subject is a planted party.

Otherwise it is 0. Detector noise and hard negatives are 0. The subject rule exists because statistical alerts cite a capped sample of a provider's lines, and that sample may miss the planted ones.

**This is the main caveat.** The labels come from the same generator that produced the data, so the models partly learn the generator. These mitigations reduce that, but do not remove it:

1. 24 independently seeded worlds with seeded scheme onsets (the `panel` profile).
2. Whole worlds held out for calibration and test.
3. One scheme type, S06 ambulance, held out of training altogether (see below).
4. Features that would only reflect generator artefacts are excluded (see Features).

## Data

- **Profile `panel`:** each world has 260 members, 48 providers, about 5,600 lines and 15 months (2024-01 to 2025-03). Scheme onsets are seeded and spread over the window (`onset_spread`), so a provider can be clean at one cutoff and start billing a scheme later. The `tiny` profile is unchanged (byte-identical output for seed 7).
- **Worlds:** generator seeds 7001–7024 (`seed × 1000 + 1..24`).
  - Train: 7001–7014.
  - Calibration: 7015–7019.
  - Test: 7020–7024.
  - Worlds are the unit of the split, so a ring never straddles train and test.
- **Rows:**
  - 16,096 provider × monthly-cutoff rows, with 12 cutoffs at months 3–14.
  - 3,286 case rows. Cases come from running the production detectors and case builder on each as-of snapshot.
- **Why not the `small` profile:** one `small` world took about 176 s to generate and 108 s to run the detectors, and it had only 15 fraud providers among 331. It is too slow to give many independent worlds inside a short training run. The audit suggested `small` because the hazard needs a longer time span. `panel` gives 15 months per world plus 24 worlds of variety in about 40–60 s of generation and detection on 8 cores.

## Features (as of the cutoff only)

Every row is computed from `snapshot.as_of(tables, t)`:

- a claim line needs both its service date and its claim's received date on or before *t*;
- deaths after *t* are masked;
- providers enrolled after *t*, and ownership links that start after *t*, are dropped;
- referrals, prescriptions, exclusions, eligibility, inpatient stays (by discharge date) and EVV are cut at *t*;
- investigation tables are removed.

The detectors then run on that snapshot. At inference, the cutoff is the extract's latest service date, so live scoring sees the same shape as training.

- **Provider features (41):**
  - alert counts by detector layer, strongest score, recency;
  - lines, paid and members over 30/90 days, billing trend;
  - peer z-score of paid per member;
  - graph degree (owner/TIN/contact, location, referral) and ring size;
  - referrals received;
  - one count per alert kind.
- **Case features (33):** alert, kind and detector counts, scores, flagged lines, dollars, members, linked NPIs, and one count per alert kind.

`features.assert_clean` rejects any feature name that matches ground truth, labels, investigation process or outcomes, queue state, identifiers, or generator artefacts:

- **Round amounts and claim lags:** planted lines are generated with round amounts and different received lags.
- **Enrolment tenure and first-seen dates:** every legitimate provider enrols before the window, while planted rings and shells enrol later.
- **Investigations:** the generator draws investigation subjects only from planted providers.

These features would score very well here and mean nothing on real data, so they are excluded on purpose.

## Models

- **Hazard:** a single discrete-time logistic hazard fitted on person-period rows (provider × cutoff × interval *k* = 1..3, with interval dummies). Each provider gets h₁, h₂, h₃, and F(k) = 1 − ∏(1 − hⱼ). Risk at 30/60/90 days is therefore monotone by construction; the backtest found 0 violations.
- **P(confirm):** a logistic classifier on case rows.
- **Shared setup for both:**
  - features are standardised and winsorised at ±4 SD, with L2 regularisation (C = 0.5);
  - Platt calibration is fitted on the calibration worlds at the last two eligible cutoffs, and skipped if either class has fewer than 5 rows;
  - each case's response lists per-feature contributions to the logit (`risk_factors`, `p_confirm_factors`);
  - the stored artifact is plain JSON (coefficients, scaling, Platt terms, feature list, metrics), with no pickle.
- **Challenger:** sklearn HistGradientBoosting, reported in the backtest only. It is not used in production; see open issues.
- **Fallback:** if no valid artifact exists (missing, corrupt, or a feature list that no longer matches the code), the pipeline uses the old fixed formulas. Every score is then marked `score_kind = "uncalibrated_heuristic"` and `calibrated = false`, and the brief says "uncalibrated heuristic, not a probability".

## Backtest design

Rolling origin, with test cutoffs at months 8, 9, 10, 11 and 12 of the five test worlds.

| Model | Fits on cutoffs | Label lag | Lag check |
| --- | --- | --- | --- |
| Hazard | ≤ T − 4 months | 30-day label lag | Every training label window (90 days + lag) closes before T |
| P(confirm) | ≤ T − 2 months | 60-day label lag | — |

For both models, calibration uses the calibration worlds at the last two eligible months. Test rows come only from unseen worlds at cutoff T.

Capacity metrics fill a 40-hour desk per (world, cutoff), greedily by score:

- providers are costed at 8 h each;
- cases are costed at the builder's estimated hours;
- precision and recall are measured over the selected rows.

Leakage tests (`tests/test_risk_leakage.py`, 22 tests) cover all six traps in the research brief:

1. Random splits: poisoning test worlds and post-fit cutoffs leaves the fit unchanged.
2. Late claims: features are invariant to post-cutoff claims, received dates and deaths.
3. Label dating: labels are dated and censored, and windows close before the test cutoff.
4. Process features: investigation tables have no effect, and process columns are rejected.
5. Ring split: providers and rings are confined to one world.
6. Generator artefacts: banned names are rejected, and features are invariant to relabelling IDs.

## Results (backtest on held-out worlds and later cutoffs)

These are measured numbers from the artifact above. They describe synthetic data only.

**30/60/90-day risk.** n = 1,423 provider rows; positive rates 11.0% / 12.8% / 13.8%; 125 providers selected at capacity.

| Horizon | Scorer | PR-AUC | ROC-AUC | Brier | ECE | Precision @ capacity | Recall @ capacity |
| --- | --- | --- | --- | --- | --- | --- | --- |
| 30d | **Trained hazard** | **0.482** | **0.852** | **0.075** | **0.031** | **0.440** | **0.353** |
| 30d | Old heuristic | 0.194 | 0.690 | 0.096 | 0.060 | 0.208 | 0.167 |
| 30d | Rules-only (rule hit count) | 0.136 | 0.553 | n/a | n/a | 0.264 | 0.212 |
| 30d | HGB challenger | 0.578 | 0.877 | 0.072 | 0.036 | 0.536 | 0.430 |
| 60d | **Trained hazard** | **0.509** | **0.821** | **0.092** | **0.051** | **0.464** | **0.319** |
| 60d | Old heuristic | 0.224 | 0.689 | 0.136 | 0.134 | 0.240 | 0.165 |
| 60d | Rules-only | 0.177 | 0.573 | n/a | n/a | 0.328 | 0.225 |
| 60d | HGB challenger | 0.541 | 0.843 | 0.096 | 0.058 | 0.552 | 0.379 |
| 90d | **Trained hazard** | **0.498** | **0.804** | **0.105** | **0.063** | **0.464** | **0.294** |
| 90d | Old heuristic | 0.233 | 0.688 | 0.180 | 0.209 | 0.248 | 0.157 |
| 90d | Rules-only | 0.195 | 0.577 | n/a | n/a | 0.344 | 0.218 |
| 90d | HGB challenger | 0.533 | 0.831 | 0.105 | 0.062 | 0.576 | 0.366 |

**P(confirm).** n = 339 test cases; positive rate 64.9%.

| Scorer | PR-AUC | ROC-AUC | Brier | ECE | Precision @ capacity | Recall @ capacity | Cases selected |
| --- | --- | --- | --- | --- | --- | --- | --- |
| **Trained model** | **0.952** | **0.892** | **0.132** | **0.088** | **1.000** | **0.341** | 75 |
| Old heuristic | 0.801 | 0.646 | 0.220 | 0.213 | 0.833 | 0.295 | 78 |
| Rules-only (rule alerts in case) | 0.705 | 0.480 | n/a | n/a | 0.840 | 0.382 | 100 |
| HGB challenger | 0.964 | 0.928 | 0.117 | 0.078 | 0.978 | 0.405 | 91 |

The selected case counts differ because cases cost different hours: the model fills 40 h with fewer, larger cases than rules-only. The rules-only baseline scores are counts, not probabilities, so they have no Brier or ECE. ECE uses 10 equal-frequency bins.

### Calibration (trained model, observed rate by predicted band)

**P(confirm):**

| Predicted band | n | Mean predicted | Observed |
| --- | --- | --- | --- |
| 0–25% | 56 | 21% | 25% |
| 25–50% | 52 | 37% | 25% |
| 50–75% | 55 | 64% | 42% |
| 75–90% | 5 | 85% | 80% |
| 90–99% | 47 | 96% | 89% |
| ≥ 99% | 124 | 99.9% | 100% |

**90-day risk:**

| Predicted band | n | Mean predicted | Observed |
| --- | --- | --- | --- |
| 0–25% | 1,124 | 9.7% | 7.0% |
| 25–50% | 129 | 36% | 26% |
| 50–75% | 77 | 63% | 36% |
| 75–90% | 51 | 83% | 45% |
| 90–99% | 23 | 95% | 70% |
| ≥ 99% | 19 | 99.8% | 95% |

The decile reliability curves are in the artifact (`metrics.*.reliability_model`). The models are well calibrated at the extremes and **over-confident in the middle**. P(confirm) predicted at 25–75% confirmed at only 25–42%. 90-day risk predicted at 50–90% occurred at only 36–45%. Treat the mid-range as "uncertain", not as the literal number.

### Recommended display bands

The queue's 25/50/75% cut-offs are placeholders. On this backtest, the 0–25% and 25–50% P(confirm) bands both confirmed at 25%, so the 25% cut-off separates nothing.

Recommended P(confirm) bands, by observed rate:

| Band | P(confirm) | Observed confirm rate | Cases |
| --- | --- | --- | --- |
| Low | < 50% | 25% | 108 |
| Uncertain | 50–90% | 45% | 60 |
| High | 90–99% | 89% | 47 |
| Very high | ≥ 99% | 100% | 124 |

For 90-day risk:

| Band | 90-day risk | Observed rate |
| --- | --- | --- |
| Low | < 25% | 7% |
| Elevated | 25–75% | about 30% |
| High | 75–99% | about 53% |
| Very high | ≥ 99% | 95% (n = 19) |

These bands come from one synthetic backtest with small counts in some bands. Re-derive them from `metrics.confirm.bands_model` and `metrics.hazard.*.bands_model` after any retrain.

### Held-out scheme type: S06 ambulance

S06 providers and cases are excluded from fitting and calibration, then scored on the unseen worlds as a new scheme type. The models **do not generalise to it**:

- **Hazard:** across 17 provider rows with an S06 event in the next 90 days, recall at capacity was 0.0 and the mean risk percentile was 0.33 (below the median).
- **P(confirm):** S06 cases got a mean P(confirm) of 0.87 from their other signals, but none made the 40-hour capacity cut (0 of 24).

This is the honest limit of a model trained on known schemes. The S06 rule still fires and still creates cases; only the learned scores miss it.

### Training time

`make train` builds 24 worlds and runs the detectors on every monthly snapshot with 8 worker processes. It then runs the 5-fold backtest, the challenger and the final fit.

| Run | Load on the shared 8-core box (load average) | Total | Build | Backtest + fit |
| --- | --- | --- | --- | --- |
| Final artifact | about 6 | 51 s | 41.7 s | 9.3 s |
| `--no-challenger` | about 9 | 65 s | 58.2 s | 6.9 s |
| Earlier runs, heavy contention | 9–11 | 105–113 s | — | — |

Two runs produced the same data hash and identical coefficients.

## Limitations

- **Synthetic only.** Labels are the generator's planted schemes, so every number here measures how well the models recover this generator's schemes on new seeds. Nothing here shows performance on real Medicaid claims.
- **Generator dependence.** Some signal may still be generator-specific even with the artefact exclusions. The HGB challenger's gap over logistic regression could partly be that.
- **Mid-range over-confidence.** See Calibration. Platt scaling sees only 5 calibration worlds × 2 cutoffs. From average row counts that is roughly 560 provider cutoffs and 115 cases, so the calibration map itself is noisy.
- **Unseen scheme types are missed.** See the S06 results.
- **Case hazard is the riskiest provider subject's curve.** Cases with no provider subject (for example member-only doctor shopping) have null 30/60/90 risk. Referral and ring schemes that plant links rather than lines create no hazard events.
- **Hyperparameters were not tuned on a separate split.** C ∈ {0.05, 0.2, 0.5, 2.0} and a calibration window of 1–4 months were inspected on the backtest folds. They made little difference, so the original defaults (C = 0.5, 2 months) were kept. This is a mild form of test-set reuse.
- **Recommend-only.** Scores order work. They never auto-label, deny, recoup or close a case. Every case keeps its evidence trail, and a human decides.
