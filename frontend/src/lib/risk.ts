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
