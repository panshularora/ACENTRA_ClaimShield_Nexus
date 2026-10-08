import type { RankFactors, RankingPolicy } from "../../api/types";

export const FACTOR_KEYS = ["severity", "exposure", "member", "evidence", "urgency"] as const;
export type FactorKey = (typeof FACTOR_KEYS)[number];

export const DEFAULT_FACTOR_LABELS: Record<FactorKey, string> = {
  severity: "Risk / scheme severity",
  exposure: "Financial exposure",
  member: "Member impact",
  evidence: "Evidence strength",
  urgency: "Urgency",
};

export interface FactorDatum {
  key: FactorKey;
  label: string;
  /** Normalised factor score, 0–1. */
  score: number;
  /** Policy weight, or null when the API did not send weights. */
  weight: number | null;
  /** Points of the 0–100 combined score (score × weight × 100). */
  points: number;
}

/** Turns API rank factors into chart rows. Contribution = score × weight. */
export function factorData(factors: RankFactors, labels: Partial<Record<FactorKey, string>> = {}): FactorDatum[] {
  return FACTOR_KEYS.map((key) => {
    const score = factors[key] ?? 0;
    const weight = factors.weights?.[key] ?? null;
    return {
      key,
      label: labels[key] ?? DEFAULT_FACTOR_LABELS[key],
      score,
      weight,
      points: weight === null ? score * 100 : score * weight * 100,
    };
  });
}

/** Ranking-policy factor labels from the run, keyed by factor. */
export function policyLabels(policy: RankingPolicy | undefined): Partial<Record<FactorKey, string>> {
  const labels: Partial<Record<FactorKey, string>> = {};
  for (const factor of policy?.factors ?? []) {
    if ((FACTOR_KEYS as readonly string[]).includes(factor.key)) labels[factor.key as FactorKey] = factor.label;
  }
  return labels;
}
