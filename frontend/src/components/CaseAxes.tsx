import type { CaseDetail, QueueCase } from "../api/types";
import { StatTile } from "./ui/StatTile";
import { hours, money, pct, screeningShort } from "../lib/format";
import { CONFIRM_BAND_LABEL, confirmBand, RISK_LABEL, riskLevel } from "../lib/risk";

type AxesCase = Pick<
  CaseDetail,
  | "p_confirm"
  | "severity"
  | "flagged_dollars"
  | "harm"
  | "members_affected"
  | "evidence_strength"
  | "screening_days_left"
  | "estimated_hours"
>;

/** Six scores, one number each. Hints do not repeat the value. */
export function CaseAxes({ data }: { data: AxesCase | QueueCase }) {
  const band = CONFIRM_BAND_LABEL[confirmBand(data.p_confirm)];
  const severityName = RISK_LABEL[riskLevel(data.severity)];
  const days = screeningShort(data.screening_days_left);
  return (
    <dl className="stat-grid case-axes">
      <StatTile label="Suspicion" value={pct(data.p_confirm)} hint={band} />
      <StatTile label="Scheme severity" value={`${data.severity} / 4`} hint={severityName} />
      <StatTile label="Financial exposure" value={money(data.flagged_dollars)} hint="Paid on flagged lines" />
      <StatTile
        label="Member impact"
        value={String(data.members_affected)}
        hint={`Harm level ${data.harm}`}
        tone={data.harm >= 3 ? "harm" : "default"}
      />
      <StatTile label="Evidence strength" value={pct(data.evidence_strength)} hint="Packet completeness" />
      <StatTile label="Urgency" value={days} hint={`${hours(data.estimated_hours)} to review`} />
    </dl>
  );
}
