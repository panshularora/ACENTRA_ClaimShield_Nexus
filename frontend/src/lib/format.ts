import type { Lane } from "../api/types";

export function money(value: number): string {
  return new Intl.NumberFormat("en-US", {
    style: "currency",
    currency: "USD",
    maximumFractionDigits: 0,
  }).format(value);
}

export function hours(value: number): string {
  return `${value.toFixed(1)}h`;
}

export function pct(value: number | null | undefined): string {
  if (value === null || value === undefined) return "—";
  return `${Math.round(value * 100)}%`;
}

export function laneLabel(lane: Lane): string {
  switch (lane) {
    case "harm_priority":
      return "Harm priority";
    case "selected":
      return "Selected";
    case "needs_evidence":
      return "Needs evidence";
    case "overflow":
      return "Monitor";
    default:
      return lane;
  }
}

export function horizonRisk(
  row: { f30: number | null; f60: number | null; f90: number | null },
  horizon: number,
): number | null {
  if (horizon <= 30) return row.f30;
  if (horizon <= 60) return row.f60;
  return row.f90;
}

export function signalLabel(evidence: Record<string, unknown>): string {
  const kind = typeof evidence.kind === "string" ? evidence.kind : "";
  const map: Record<string, string> = {
    duplicate: "Duplicate billing",
    ptp_pair: "Unbundling (PTP)",
    unit_cap: "Units over cap",
    after_death: "Service after death",
    daily_minutes_cap: "Impossible daily hours",
    inpatient_overlap: "Billed during inpatient stay",
    evv_missing: "Home visit without EVV",
    excluded_party: "Excluded-party NPI",
    doctor_shopping: "Doctor shopping",
    sex_implausible: "Sex-implausible procedure",
    pos_mismatch: "Place-of-service mismatch",
    ambulance_overlap: "Overlapping ambulance trips",
    clone_billing: "Clone billing",
    em_upcode_z: "E/M mix vs peers",
    hh_iqr: "Home-health volume fence",
    genetic_mill: "Genetic-testing mill",
  };
  return map[kind] ?? kind.replaceAll("_", " ") ?? "Signal";
}

export function whyPriority(row: {
  lane: Lane;
  harm: number;
  p_confirm: number;
  flagged_dollars: number;
  evidence_strength: number;
}): string {
  if (row.lane === "harm_priority") {
    return `Harm ${row.harm} overrides capacity — always queued.`;
  }
  if (row.lane === "needs_evidence") {
    return `Evidence ${pct(row.evidence_strength)} is below the 0.40 floor.`;
  }
  if (row.lane === "overflow") {
    return "Outside remaining investigator hours after knapsack fill.";
  }
  return `Selected: P(confirm) ${pct(row.p_confirm)} on ${money(row.flagged_dollars)} flagged.`;
}
