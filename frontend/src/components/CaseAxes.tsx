import type { CaseDetail, QueueCase } from "../api/types";
import { ConfirmBandBadge, HarmFlag, RiskBadge } from "./Badge";
import { EvidenceBar } from "./EvidenceBar";
import { StatTile } from "./ui/StatTile";
import { hours, money, pct, screeningLabel, screeningShort } from "../lib/format";
import { SCORE_LABELS } from "../lib/scoreLabels";

type AxesCase = Pick<
  CaseDetail,
  "p_confirm" | "severity" | "flagged_dollars" | "harm" | "members_affected" | "evidence_strength" | "screening_days_left" | "estimated_hours" | "score_kind" | "calibrated"
>;

/** The six scores an SIU reviewer should read on every case. */
export function CaseAxes({ data }: { data: AxesCase | QueueCase }) {
  return (
    <dl className="stat-grid case-axes">
      <StatTile
        label="Suspicion"
        value={
          <span className="axis-pair">
            <ConfirmBandBadge p={data.p_confirm} />
            <span className="num">{pct(data.p_confirm)}</span>
          </span>
        }
        hint={SCORE_LABELS.pConfirm.hintFor(data)}
      />
      <StatTile
        label="Scheme severity"
        value={<RiskBadge severity={data.severity} />}
        hint={`${data.severity} of 4`}
      />
      <StatTile
        label="Financial exposure"
        value={money(data.flagged_dollars)}
        hint="Already paid on flagged claims"
      />
      <StatTile
        label="Member impact"
        value={<HarmFlag harm={data.harm} />}
        hint={`${data.members_affected} people on flagged claims. Desk rank uses this, not the suspicion score.`}
        tone={data.harm >= 3 ? "harm" : "default"}
      />
      <StatTile
        label="Evidence strength"
        value={<EvidenceBar value={data.evidence_strength} label="Evidence strength" />}
        hint={pct(data.evidence_strength)}
      />
      <StatTile
        label="Urgency"
        value={screeningShort(data.screening_days_left)}
        hint={screeningLabel(data.screening_days_left) + ` · ${hours(data.estimated_hours)} to review`}
      />
    </dl>
  );
}
