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

/** Queue lanes in desk order: harm first, then selected, evidence, backlog. */
export const LANE_ORDER: Lane[] = ["harm_priority", "selected", "needs_evidence", "overflow"];

export function laneLabel(lane: Lane): string {
  switch (lane) {
    case "harm_priority":
      return "Harm priority";
    case "selected":
      return "Selected";
    case "needs_evidence":
      return "Needs evidence";
    case "overflow":
      return "Tracked backlog";
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
  why_rank?: { code: string; text: string };
}): string {
  if (row.why_rank?.text) return row.why_rank.text;
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

export function screeningLabel(days: number | null | undefined): string {
  if (days === null || days === undefined) return "No screening clock";
  if (days < 0) return `${Math.abs(days)}d past 45-day screen`;
  return `${days}d left on 45-day screen`;
}

export function screeningShort(days: number | null | undefined): string {
  if (days === null || days === undefined) return "—";
  if (days < 0) return `${Math.abs(days)}d past`;
  return `${days}d`;
}

export function screeningTone(days: number | null | undefined): "ok" | "warn" | "hot" | "none" {
  if (days === null || days === undefined) return "none";
  if (days <= 7) return "hot";
  if (days <= 15) return "warn";
  return "ok";
}

export function compactMoney(value: number): string {
  return new Intl.NumberFormat("en-US", {
    style: "currency",
    currency: "USD",
    notation: "compact",
    maximumFractionDigits: 1,
  }).format(value);
}

export function count(value: number, noun: string, plural = `${noun}s`): string {
  return `${value.toLocaleString("en-US")} ${value === 1 ? noun : plural}`;
}

const monthDay = new Intl.DateTimeFormat("en-US", { month: "short", day: "numeric", timeZone: "UTC" });
const monthYear = new Intl.DateTimeFormat("en-US", { month: "short", year: "numeric", timeZone: "UTC" });

/** Formats a UTC epoch-ms date as "Jan 4". */
export function shortDate(ms: number): string {
  return monthDay.format(ms);
}

/** Formats a UTC epoch-ms date as "Jan 2024". */
export function monthLabel(ms: number): string {
  return monthYear.format(ms);
}

/** Parses an ISO date (YYYY-MM-DD) to UTC epoch ms, or null when absent/invalid. */
export function isoDateMs(value: string | null | undefined): number | null {
  if (!value) return null;
  const ms = Date.parse(`${value.slice(0, 10)}T00:00:00Z`);
  return Number.isNaN(ms) ? null : ms;
}

/** Start (Monday, UTC) of the ISO week containing the given epoch-ms date. */
export function weekStartMs(ms: number): number {
  const date = new Date(ms);
  const offset = (date.getUTCDay() + 6) % 7;
  return Date.UTC(date.getUTCFullYear(), date.getUTCMonth(), date.getUTCDate() - offset);
}

export function humanize(value: string): string {
  const text = value.replaceAll("_", " ");
  return text.charAt(0).toUpperCase() + text.slice(1);
}

// dateStyle/timeStyle cannot be combined with timeZoneName, so the fields are spelled out.
const dateTimeFormat = new Intl.DateTimeFormat("en-GB", {
  day: "numeric",
  month: "short",
  year: "numeric",
  hour: "2-digit",
  minute: "2-digit",
  timeZoneName: "short",
});

/** Formats an ISO timestamp in the viewer's time zone, with a zone label; falls back to the raw text. */
export function dateTime(value: string | null | undefined): string {
  if (!value) return "—";
  const ms = Date.parse(value);
  return Number.isNaN(ms) ? value : dateTimeFormat.format(ms);
}
