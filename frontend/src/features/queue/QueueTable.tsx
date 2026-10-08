import type { QueueCase } from "../../api/types";
import { HarmFlag, LaneBadge, RiskBadge, StatusBadge } from "../../components/Badge";
import { EvidenceBar } from "../../components/EvidenceBar";
import { horizonRisk, hours, money, pct, screeningLabel, screeningShort, screeningTone, whyPriority } from "../../lib/format";
import { FactorStrip } from "./FactorBars";
import { SCORE_LABELS } from "../../lib/scoreLabels";
import type { OverrideTarget } from "./OverrideForm";

export type SortKey = "rank" | "ev" | "dollars" | "harm" | "hours" | "evidence" | "p";

interface QueueTableProps {
  rows: QueueCase[];
  horizon: number;
  openId: string | null;
  compareIds: string[];
  canOverride: boolean;
  onOpen: (caseId: string) => void;
  onCompare: (caseId: string) => void;
  onOverride: (target: OverrideTarget) => void;
}

/** Ranked queue as a semantic table. Each case id is a button that opens the case drawer. */
export function QueueTable({ rows, horizon, openId, compareIds, canOverride, onOpen, onCompare, onOverride }: QueueTableProps) {
  return (
    <div className="table-wrap queue-wrap">
      <table className="grid queue-grid">
        <caption className="sr-only">Ranked SIU cases with lane, deadlines, value, harm, evidence and rank factors</caption>
        <thead>
          <tr>
            <th scope="col" className="check">
              <span className="sr-only">Compare</span>
            </th>
            <th scope="col">Case</th>
            <th scope="col">Lane</th>
            <th scope="col">Status</th>
            <th scope="col" className="num" title="Days left on the 45-day screening window">
              45-day
            </th>
            <th scope="col" className="num">
              {SCORE_LABELS.pConfirm.label}
            </th>
            <th scope="col" className="num">
              {SCORE_LABELS.horizon.label(horizon)}
            </th>
            <th scope="col" className="num" title={SCORE_LABELS.expectedValue.hint}>
              {SCORE_LABELS.expectedValue.label}
            </th>
            <th scope="col" className="num">
              Flagged
            </th>
            <th scope="col" className="num">
              Members
            </th>
            <th scope="col">Risk</th>
            <th scope="col">Harm</th>
            <th scope="col">Evidence</th>
            <th scope="col" className="num">
              Hours
            </th>
            <th scope="col">Rank factors</th>
            {canOverride ? <th scope="col">Override</th> : null}
          </tr>
        </thead>
        <tbody>
          {rows.map((row) => (
            <QueueRow
              key={row.case_id}
              row={row}
              horizon={horizon}
              open={openId === row.case_id}
              compared={compareIds.includes(row.case_id)}
              canOverride={canOverride}
              onOpen={onOpen}
              onCompare={onCompare}
              onOverride={onOverride}
            />
          ))}
        </tbody>
      </table>
    </div>
  );
}

interface QueueRowProps {
  row: QueueCase;
  horizon: number;
  open: boolean;
  compared: boolean;
  canOverride: boolean;
  onOpen: (caseId: string) => void;
  onCompare: (caseId: string) => void;
  onOverride: (target: OverrideTarget) => void;
}

function QueueRow({ row, horizon, open, compared, canOverride, onOpen, onCompare, onOverride }: QueueRowProps) {
  const onDesk = row.lane === "harm_priority" || row.lane === "selected";
  const group = row.alert_group;
  return (
    <tr className={`lane-${row.lane} ${open ? "is-open" : ""}`}>
      <td className="check">
        <input
          type="checkbox"
          aria-label={`Compare ${row.case_id}`}
          checked={compared}
          onChange={() => onCompare(row.case_id)}
        />
      </td>
      <th scope="row" className="case-cell">
        <span className="case-id-row">
          <button
            type="button"
            className="link-button mono"
            aria-haspopup="dialog"
            title={whyPriority(row)}
            onClick={() => onOpen(row.case_id)}
          >
            {row.case_id}
          </button>
          {row.queue_rank ? <span className="badge today-rank">#{row.queue_rank}</span> : null}
        </span>
        <span className="mono muted">{row.primary_entity_id}</span>
        {group ? (
          <span className="muted" title={group.text}>
            {group.n_alerts ? `${group.n_alerts} grouped alerts` : "Grouped alerts"}
            {group.n_entities > 1 ? ` · ${group.n_entities} linked NPIs` : ""}
            {group.urgent ? " · urgent" : ""}
          </span>
        ) : null}
        {row.override ? <span className="muted">Human {row.override.action}</span> : null}
      </th>
      <td>
        <LaneBadge lane={row.lane} />
      </td>
      <td>
        <StatusBadge status={row.status} />
      </td>
      <td className="num">
        <span className={`sla-chip sla-${screeningTone(row.screening_days_left)}`} title={screeningLabel(row.screening_days_left)}>
          {screeningShort(row.screening_days_left)}
        </span>
      </td>
      <td className="num">{pct(row.p_confirm)}</td>
      <td className="num">{pct(horizonRisk(row, horizon))}</td>
      <td className="num">{money(row.expected_value ?? 0)}</td>
      <td className="num dollars">{money(row.flagged_dollars)}</td>
      <td className="num">{row.members_affected}</td>
      <td>
        <RiskBadge severity={row.severity} />
      </td>
      <td>
        <HarmFlag harm={row.harm} />
      </td>
      <td>
        <EvidenceBar value={row.evidence_strength} />
      </td>
      <td className="num">{hours(row.estimated_hours)}</td>
      <td className="factors-cell">
        <FactorStrip factors={row.rank_factors} />
      </td>
      {canOverride ? (
        <td>
          <button
            type="button"
            className="btn small ghost"
            aria-label={`${onDesk ? "Defer" : "Promote"} ${row.case_id}`}
            onClick={() => onOverride({ caseId: row.case_id, action: onDesk ? "defer" : "promote" })}
          >
            {onDesk ? "Defer" : "Promote"}
          </button>
        </td>
      ) : null}
    </tr>
  );
}
