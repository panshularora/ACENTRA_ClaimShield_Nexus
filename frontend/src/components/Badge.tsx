import type { Lane } from "../api/types";
import { laneLabel } from "../lib/format";
import {
  CONFIRM_BAND_LABEL,
  confirmBand,
  RISK_GLYPH,
  RISK_LABEL,
  riskLevel,
  type ConfirmBand,
  type RiskLevel,
} from "../lib/risk";

/** Workflow lane as a neutral chip (lanes are not risk). */
export function LaneBadge({ lane }: { lane: Lane }) {
  return <span className={`badge lane-${lane}`}>{laneLabel(lane)}</span>;
}

export function StatusBadge({ status }: { status: string }) {
  return <span className="badge status">{status}</span>;
}

/** Case risk level from API severity (1–4): glyph + label + colour, never colour alone. */
export function RiskBadge({ severity }: { severity: number }) {
  return <RiskLevelBadge level={riskLevel(severity)} title={`Severity ${severity} of 4`} />;
}

export function RiskLevelBadge({ level, title }: { level: RiskLevel; title?: string }) {
  return (
    <span className={`badge risk-${level}`} title={title}>
      <span aria-hidden="true">{RISK_GLYPH[level]}</span>
      {RISK_LABEL[level]}
      <span className="sr-only"> risk</span>
    </span>
  );
}

/** Patient harm, a separate axis from risk. Flagged at 3 and above; lower levels print as muted numbers. */
export function ConfirmBandBadge({ p }: { p: number }) {
  const band: ConfirmBand = confirmBand(p);
  return (
    <span className={`badge confirm-${band}`} title="P(confirm) band; not a finding">
      {CONFIRM_BAND_LABEL[band]}
    </span>
  );
}

export function HarmFlag({ harm }: { harm: number }) {
  if (harm < 3) {
    return (
      <span className="harm-level num" title="Patient-harm level (separate from financial risk)">
        <span className="sr-only">Harm </span>
        {harm}
      </span>
    );
  }
  return (
    <span className="badge harm" title="Patient-harm level (separate from financial risk)">
      <span aria-hidden="true">✚</span>Harm {harm}
    </span>
  );
}
