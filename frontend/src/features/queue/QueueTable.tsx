import type { QueueCase } from "../../api/types";
import { ConfirmBandBadge, HarmFlag, LaneBadge, RiskBadge, StatusBadge } from "../../components/Badge";
import { EvidenceBar } from "../../components/EvidenceBar";
import { money, pct, screeningLabel, screeningShort, screeningTone, whyPriority } from "../../lib/format";
import { FactorStrip } from "./FactorBars";
import { DASH_LABEL, SCORE_LABELS } from "../../lib/scoreLabels";
import type { OverrideTarget } from "./OverrideForm";

export type SortKey = "rank" | "p" | "severity" | "dollars" | "harm" | "evidence" | "hours";

interface QueueTableProps {
  rows: QueueCase[];
  openId: string | null;
  compareIds: string[];
  canOverride: boolean;
  onOpen: (caseId: string) => void;
  onCompare: (caseId: string) => void;
  onOverride: (target: OverrideTarget) => void;
}

/** Ranked queue as a semantic table. Each case id is a button that opens the case drawer. */
export function QueueTable({ rows, openId, compareIds, canOverride, onOpen, onCompare, onOverride }: QueueTableProps) {
  return (
    <div className="table-wrap queue-wrap">
      <table className="grid queue-grid">
        <caption className="sr-only">
          Ranked SIU cases with suspicion, scheme severity, financial exposure, member impact, evidence strength and urgency
        </caption>
        <colgroup>
          <col className="col-check" />
          <col className="col-case" />
          <col className="col-lane" />
          <col className="col-status" />
          <col className="col-suspicion" />
          <col className="col-harm" />
          <col className="col-money" />
          <col className="col-harm" />
          <col className="col-proof" />
          <col className="col-num" />
          <col className="col-why" />
          {canOverride ? <col className="col-move" /> : null}
        </colgroup>
        <thead>
          <tr>
            <th scope="col" className="check">
              <span className="sr-only">Compare</span>
            </th>
            <th scope="col">{DASH_LABEL.case}</th>
            <th scope="col">{DASH_LABEL.lane}</th>
            <th scope="col">{DASH_LABEL.status}</th>
            <th scope="col" title={SCORE_LABELS.pConfirm.hint}>
              {DASH_LABEL.chance}
            </th>
            <th scope="col" title="How serious the billed pattern looks (1–4)">
              {DASH_LABEL.severity}
            </th>
            <th scope="col" className="num" title="Dollars already paid on flagged claims">
              {DASH_LABEL.paid}
            </th>
            <th scope="col" title="Patient-harm level and people on flagged claims">
              {DASH_LABEL.harm}
            </th>
            <th scope="col">{DASH_LABEL.proof}</th>
            <th scope="col" className="num" title="Days left on the 45-day screening clock">
              {DASH_LABEL.time}
            </th>
            <th scope="col">{DASH_LABEL.why}</th>
            {canOverride ? <th scope="col">{DASH_LABEL.move}</th> : null}
          </tr>
        </thead>
        <tbody>
          {rows.map((row) => (
            <QueueRow
              key={row.case_id}
              row={row}
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
  open: boolean;
  compared: boolean;
  canOverride: boolean;
  onOpen: (caseId: string) => void;
  onCompare: (caseId: string) => void;
  onOverride: (target: OverrideTarget) => void;
}

function QueueRow({ row, open, compared, canOverride, onOpen, onCompare, onOverride }: QueueRowProps) {
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
            {group.n_alerts ? `${group.n_alerts} patterns reviewed together` : "Patterns reviewed together"}
            {group.n_entities > 1 ? ` · ${group.n_entities} linked providers` : ""}
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
      <td title={SCORE_LABELS.pConfirm.hint}>
        <span className="axis-pair">
          <ConfirmBandBadge p={row.p_confirm} />
          <span className="num">{pct(row.p_confirm)}</span>
        </span>
      </td>
      <td>
        <RiskBadge severity={row.severity} />
      </td>
      <td className="num dollars">{money(row.flagged_dollars)}</td>
      <td>
        <span className="axis-pair">
          <HarmFlag harm={row.harm} />
          <span className="muted">{row.members_affected} people</span>
        </span>
      </td>
      <td>
        <EvidenceBar value={row.evidence_strength} label={DASH_LABEL.proof} />
      </td>
      <td className="num">
        <span className={`sla-chip sla-${screeningTone(row.screening_days_left)}`} title={screeningLabel(row.screening_days_left)}>
          {screeningShort(row.screening_days_left)}
        </span>
      </td>
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
