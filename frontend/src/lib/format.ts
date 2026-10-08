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

/** 0–1 score as a 0–99 integer. Never 100 — scores are not certainty. */
export function pctNumber(value: number | null | undefined): number | null {
  if (value === null || value === undefined || Number.isNaN(Number(value))) return null;
  return Math.min(99, Math.max(0, Math.round(Number(value) * 100)));
}

/** Percent for display. Never prints 100% — scores are not certainty. */
export function pct(value: number | null | undefined): string {
  const n = pctNumber(value);
  return n === null ? "—" : `${n}%`;
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

/**
 * Neutral display names for detector patterns, keyed by alert evidence `kind`.
 * They describe what was measured, never intent ("mill", "padding", "doctor shopping" and
 * "clone" are replaced), and take precedence over the API's own labels.
 */
export const PATTERN_LABELS: Record<string, string> = {
  duplicate: "Possible duplicate lines",
  ptp_pair: "NCCI procedure-pair edit",
  unit_cap: "Units over cap",
  after_death: "Service after date of death",
  daily_minutes_cap: "Daily hours over plausible cap",
  inpatient_overlap: "Billed during inpatient stay",
  evv_missing: "Home visit without EVV",
  excluded_party: "Possible exclusion-list match",
  doctor_shopping: "Many prescribers for one member",
  sex_implausible: "Procedure unusual for recorded sex",
  pos_mismatch: "Place-of-service mismatch",
  ambulance_overlap: "Overlapping ambulance trips",
  clone_billing: "Repeated identical claim amounts",
  stay_compression: "Same-day high-DRG stay",
  mileage_padding: "Ambulance mileage above urban norm",
  identity_ring: "Shared identity across NPIs",
  referral_monopoly: "Concentrated referral volume",
  excluded_owner: "Owner on exclusion list",
  em_upcode_z: "E/M level mix vs peers",
  hh_iqr: "Home-health volume above peer fence",
  genetic_mill: "High genetic-testing order volume",
};

/** The API's labels for the same kinds, so claim-line signals (which carry no kind) map too. */
const PATTERN_BY_API_LABEL: Record<string, string> = {
  "Duplicate billing": PATTERN_LABELS.duplicate,
  "Unbundling (PTP)": PATTERN_LABELS.ptp_pair,
  "Impossible daily hours": PATTERN_LABELS.daily_minutes_cap,
  "Excluded-party NPI": PATTERN_LABELS.excluded_party,
  "Doctor shopping": PATTERN_LABELS.doctor_shopping,
  "Sex-implausible procedure": PATTERN_LABELS.sex_implausible,
  "Clone billing": PATTERN_LABELS.clone_billing,
  "Urban ambulance mileage padding": PATTERN_LABELS.mileage_padding,
  "Genetic-testing mill": PATTERN_LABELS.genetic_mill,
  "Home-health volume fence": PATTERN_LABELS.hh_iqr,
};

/** Display name for an API pattern label (neutral wording where we have one). */
export function neutralLabel(label: string): string {
  return PATTERN_BY_API_LABEL[label] ?? label;
}

export function signalLabel(evidence: Record<string, unknown>): string {
  const kind = typeof evidence.kind === "string" ? evidence.kind : "";
  return PATTERN_LABELS[kind] ?? (kind ? humanize(kind) : "Signal");
}

/** Display name for an alert: neutral pattern name by kind, then the API's label or rule title. */
export function alertLabel(alert: {
  evidence: Record<string, unknown>;
  label?: string | null;
  rule_title?: string | null;
  rule_id: string | null;
  detector: string;
}): string {
  const kind = typeof alert.evidence.kind === "string" ? alert.evidence.kind : "";
  const fromApi = alert.label ?? alert.rule_title;
  return PATTERN_LABELS[kind] ?? (fromApi ? neutralLabel(fromApi) : (alert.rule_id ?? alert.detector));
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
    return `Harm ${row.harm} jumps the line for member safety — always on the desk.`;
  }
  if (row.lane === "needs_evidence") {
    return `Evidence ${pct(row.evidence_strength)} is below the 40% floor, so this waits for more records.`;
  }
  if (row.lane === "overflow") {
    return "Outside remaining investigator hours after the desk is filled.";
  }
  return `On today's desk: suspicion ${pct(row.p_confirm)} on ${money(row.flagged_dollars)} already paid.`;
}

export function screeningLabel(days: number | null | undefined): string {
  if (days === null || days === undefined) return "No screening clock";
  if (days < 0) return `${Math.abs(days)}d past the 45-day screening clock`;
  return `${days}d left on the 45-day screening clock`;
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
