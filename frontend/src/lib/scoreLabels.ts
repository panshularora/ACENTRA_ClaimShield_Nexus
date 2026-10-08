/**
 * Display copy for the API's risk numbers (p_confirm, f30/f60/f90, expected_value).
 *
 * Every label, hint and chart sentence that names these scores lives here, so the wording
 * changes in one place. Definitions and backtest numbers: docs/MODEL_CARD.md.
 */
export const SCORE_LABELS = {
  pConfirm: {
    label: "P(confirm)",
    hint: "Score from the API, not a finding",
    /** Hint that says which scorer produced the number (`score_kind` / `calibrated`). */
    hintFor: (row: { score_kind?: string; calibrated?: boolean }) =>
      row.score_kind === "trained_model"
        ? row.calibrated
          ? "Calibrated model, trained on synthetic data; not a finding"
          : "Uncalibrated model score; not a finding"
        : row.score_kind === "uncalibrated_heuristic"
          ? "Heuristic fallback (trained model unavailable); not a calibrated probability"
          : "Score from the API, not a finding",
  },
  expectedValue: {
    label: "Expected value",
    hint: "Expected recoveries in dollars (P(confirm) × flagged paid)",
  },
  horizon: {
    /** Column or tile label for one horizon, e.g. "60-day risk". */
    label: (days: number) => `${days}-day risk`,
    shortSet: "F30 / F60 / F90",
    chartTitle: "Cumulative risk by horizon",
    /** Lead-in for the chart's text summary. */
    meaning:
      "Chance the case's riskiest provider bills a fraudulent claim line within each horizon (cumulative)",
    tooltip: "Cumulative risk",
  },
} as const;
