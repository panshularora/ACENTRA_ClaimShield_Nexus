/**
 * Display copy for the API's risk numbers (p_confirm, f30/f60/f90, expected_value).
 *
 * The backend definitions of these scores are being revised on a separate branch, so every
 * label, hint and chart sentence that names them lives here. Change the wording in one place
 * when the API changes.
 */
export const SCORE_LABELS = {
  pConfirm: {
    label: "P(confirm)",
    hint: "Score from the API, not a finding",
  },
  expectedValue: {
    label: "Expected value",
    hint: "P(confirm) × recovery × exposure, plus a harm term; not pure dollars",
  },
  horizon: {
    /** Column or tile label for one horizon, e.g. "60-day risk". */
    label: (days: number) => `${days}-day risk`,
    shortSet: "F30 / F60 / F90",
    chartTitle: "Cumulative risk by horizon",
    /** Lead-in for the chart's text summary. */
    meaning: "Chance the escalation event has already happened by each horizon (cumulative)",
    tooltip: "Cumulative risk",
  },
} as const;
