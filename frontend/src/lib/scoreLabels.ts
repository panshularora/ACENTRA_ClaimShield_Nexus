/**
 * Display copy for the API's risk numbers (p_confirm, f30/f60/f90, expected_value).
 *
 * `short` is the one-word dashboard column. `label` is the case-file wording.
 * Definitions and backtest numbers: docs/MODEL_CARD.md.
 */
export const SCORE_LABELS = {
  pConfirm: {
    short: "Suspicion",
    label: "Suspicion",
    hint: "Model score for review. It is not the desk rank, and it is not a finding.",
    /** Hint that says which scorer produced the number (`score_kind` / `calibrated`). */
    hintFor: (row: { score_kind?: string; calibrated?: boolean }) =>
      row.score_kind === "trained_model"
        ? row.calibrated
          ? "Learned suspicion score, adjusted to past reviews. Not desk rank. A person still decides."
          : "Learned suspicion score, not yet adjusted to past reviews. Not desk rank."
        : row.score_kind === "uncalibrated_heuristic"
          ? "Simple suspicion score. Not desk rank."
          : "Suspicion score from the case file. Not desk rank.",
  },
  expectedValue: {
    short: "Value",
    label: "Likely recovery",
    hint: "Suspicion score × dollars already paid on flagged claims",
  },
  horizon: {
    short: "Risk",
    /** Column or tile label for one window, e.g. "60-day risk". */
    label: (days: number) => `${days}-day risk`,
    shortSet: "30 / 60 / 90-day risk",
    chartTitle: "Suspicion over 30, 60 and 90 days",
    /** Lead-in for the chart's text summary. */
    meaning:
      "How the suspicion score grows if we look 30, 60 or 90 days out. Longer windows score higher. Still a score.",
    tooltip: "Suspicion by this day",
  },
} as const;

/** One-word column names for the manager queue and investigator worklist. */
export const DASH_LABEL = {
  case: "Case",
  lane: "Lane",
  status: "Status",
  clock: "Clock",
  chance: "Suspicion",
  severity: "Severity",
  risk: "Risk",
  value: "Value",
  paid: "Exposure",
  people: "People",
  harm: "Impact",
  proof: "Evidence",
  time: "Urgency",
  why: "Why",
  move: "Move",
} as const;
