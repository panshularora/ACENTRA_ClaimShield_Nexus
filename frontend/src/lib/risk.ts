/** Risk scale shared by badges, graph rings and charts (design system §2.4). */
export type RiskLevel = "low" | "medium" | "high" | "critical";

export const RISK_LEVELS: readonly RiskLevel[] = ["low", "medium", "high", "critical"];
export const RISK_GLYPH: Record<RiskLevel, string> = { low: "○", medium: "◐", high: "●", critical: "◆" };
export const RISK_LABEL: Record<RiskLevel, string> = { low: "Low", medium: "Medium", high: "High", critical: "Critical" };

/** Maps the API's case severity (1–4) onto the four risk levels. */
export function riskLevel(severity: number): RiskLevel {
  const index = Math.min(4, Math.max(1, Math.round(severity))) - 1;
  return RISK_LEVELS[index];
}

/**
 * P(confirm) display bands. Calibration is over-confident in the middle, so the
 * old 25/50/75 cut-offs are not used.
 */
export type ConfirmBand = "under50" | "mid" | "high" | "nearCertain";

export const CONFIRM_BAND_LABEL: Record<ConfirmBand, string> = {
  under50: "Under 50%",
  mid: "50–90%",
  high: "90–99%",
  nearCertain: "99% or more",
};

export function confirmBand(p: number): ConfirmBand {
  if (p < 0.5) return "under50";
  if (p < 0.9) return "mid";
  if (p < 0.99) return "high";
  return "nearCertain";
}

/** Fallback ring colour when only a probability is present (no severity). */
export function riskLevelFromConfirm(p: number): RiskLevel {
  const band = confirmBand(p);
  if (band === "under50") return "low";
  if (band === "mid") return "medium";
  if (band === "high") return "high";
  return "critical";
}
