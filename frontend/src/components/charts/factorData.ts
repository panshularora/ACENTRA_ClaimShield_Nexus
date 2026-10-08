import type { RankFactors, RankingPolicy } from "../../api/types";
import { pctNumber } from "../../lib/format";

export const FACTOR_KEYS = ["severity", "exposure", "member", "evidence", "urgency"] as const;
export type FactorKey = (typeof FACTOR_KEYS)[number];

export const DEFAULT_FACTOR_LABELS: Record<FactorKey, string> = {
  severity: "Scheme severity",
  exposure: "Financial exposure",
  member: "Member impact",
  evidence: "Evidence strength",
  urgency: "Urgency",
};

/** One-word names for the queue legend. */
export const SHORT_FACTOR_LABELS: Record<FactorKey, string> = {
  severity: "Severity",
  exposure: "Exposure",
  member: "Impact",
  evidence: "Evidence",
  urgency: "Urgency",
};

/** Chart token per ranking factor — same colours as the queue strip. */
export const FACTOR_COLOR_TOKEN: Record<FactorKey, `--${string}`> = {
  severity: "--chart-6",
  exposure: "--chart-4",
  member: "--chart-5",
  evidence: "--chart-1",
  urgency: "--chart-3",
};

export interface FactorDatum {
  key: FactorKey;
  label: string;
  /** Normalised factor score, 0–1. */
  score: number;
  /** Same 0–99 integer the case tiles use (never 100). */
  scorePts: number;
  /** Policy weight, or null when the API did not send weights. */
  weight: number | null;
  /** Points of the 0–100 desk rank (score × weight × 100). */
  points: number;
  /** Y-axis label: case score plus the name, so 93 matches the evidence tile. */
  axisLabel: string;
}

/** Turns API rank factors into chart rows. Contribution = score × weight. */
export function factorData(factors: RankFactors, labels: Partial<Record<FactorKey, string>> = {}): FactorDatum[] {
  return FACTOR_KEYS.map((key) => {
    const score = factors[key] ?? 0;
    const weight = factors.weights?.[key] ?? null;
    const scorePts = pctNumber(score) ?? 0;
    const label = labels[key] ?? DEFAULT_FACTOR_LABELS[key];
    return {
      key,
      label,
      score,
      scorePts,
      weight,
      points: weight === null ? score * 100 : score * weight * 100,
      axisLabel: `${label} (${scorePts})`,
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
