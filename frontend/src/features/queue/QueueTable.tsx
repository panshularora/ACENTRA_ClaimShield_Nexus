import type { QueueCase, RankFactors } from "../../api/types";
import { HarmFlag, LaneBadge, StatusBadge } from "../../components/Badge";
import { EvidenceBar } from "../../components/EvidenceBar";
import { FACTOR_KEYS, SHORT_FACTOR_LABELS } from "../../components/charts/factorData";
import { hours, money, pct, screeningLabel, screeningTone, whyPriority } from "../../lib/format";
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
          <col className="col-clock" />
          <col className="col-suspicion" />
          <col className="col-harm" />
          <col className="col-money" />
          <col className="col-num" />
          <col className="col-harm" />
          <col className="col-proof" />
          <col className="col-num" />
          <col className="col-factors" />
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
            <th scope="col" title="Days left on the 45-day screening clock">
              45-day
            </th>
            <th scope="col" title={SCORE_LABELS.pConfirm.hint}>
              {DASH_LABEL.chance}
            </th>
            <th scope="col" title="How serious the billed pattern looks (1–4)">
              {DASH_LABEL.severity}
            </th>
            <th scope="col" className="num" title="Dollars already paid on flagged claims">
              {DASH_LABEL.paid}
            </th>
            <th scope="col" className="num" title="People on flagged claims">
              Members
            </th>
            <th scope="col" title="Patient-harm level, separate from money">
              Harm
            </th>
            <th scope="col">{DASH_LABEL.proof}</th>
            <th scope="col" className="num" title="Hours packed for this case">
              Hours
            </th>
            <th scope="col" title="Severity, exposure, member impact, evidence, urgency">
              Factors
            </th>
            {canOverride ? <th scope="col">Override</th> : null}
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

function clockChip(days: number | null | undefined): string {
  if (days === null || days === undefined) return "—";
  if (days < 0) return `${Math.abs(days)}d past`;
  return `${days}d`;
}

function groupLine(row: QueueCase): string | null {
  const group = row.alert_group;
  if (!group) return null;
  const bits: string[] = [];
  if (group.n_alerts) bits.push(`${group.n_alerts} grouped alert${group.n_alerts === 1 ? "" : "s"}`);
  if (group.n_entities > 1) bits.push(`${group.n_entities} linked NPIs`);
  if (group.urgent) bits.push("urgent still visible");
  return bits.join(" · ") || group.text;
}

function FactorDots({ factors }: { factors?: RankFactors }) {
  if (!factors) return <span className="muted">—</span>;
  return (
    <span className="factor-dots" aria-label="Rank factors">
      {FACTOR_KEYS.map((key) => (
        <i
          key={key}
          className={(factors[key] ?? 0) >= 0.5 ? "is-on" : undefined}
          title={`${SHORT_FACTOR_LABELS[key]} ${pct(factors[key])}`}
        />
      ))}
    </span>
  );
}

function QueueRow({ row, open, compared, canOverride, onOpen, onCompare, onOverride }: QueueRowProps) {
  const onDesk = row.lane === "harm_priority" || row.lane === "selected";
  const why = whyPriority(row);
  const grouped = groupLine(row);
  return (
    <tr
      className={`lane-${row.lane} is-clickable ${open ? "is-open" : ""}`}
      onClick={() => onOpen(row.case_id)}
    >
      <td className="check">
        <input
          type="checkbox"
          aria-label={`Compare ${row.case_id}`}
          checked={compared}
          onClick={(event) => event.stopPropagation()}
          onChange={() => onCompare(row.case_id)}
        />
      </td>
      <th scope="row" className="case-cell">
        <span className="case-id-row">
          <button
            type="button"
            className="link-button mono"
            aria-haspopup="dialog"
            title={why}
            onClick={(event) => {
              event.stopPropagation();
              onOpen(row.case_id);
            }}
          >
            {row.case_id}
          </button>
          {row.queue_rank ? <span className="badge today-rank">#{row.queue_rank}</span> : null}
        </span>
        <span className="mono muted">{row.primary_entity_id}</span>
        {grouped ? (
          <span className="muted case-group" title={row.alert_group?.text ?? why}>
            {grouped}
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
          {clockChip(row.screening_days_left)}
        </span>
      </td>
      <td className="num" title={SCORE_LABELS.pConfirm.hint}>
        {pct(row.p_confirm)}
      </td>
      <td className="num" title={`Severity ${row.severity} of 4`}>
        {row.severity}/4
      </td>
      <td className="num dollars">{money(row.flagged_dollars)}</td>
      <td className="num">{row.members_affected}</td>
      <td>
        <HarmFlag harm={row.harm} />
      </td>
      <td>
        <EvidenceBar value={row.evidence_strength} label={DASH_LABEL.proof} />
      </td>
      <td className="num">{hours(row.estimated_hours)}</td>
      <td className="factors-cell">
        <FactorDots factors={row.rank_factors} />
      </td>
      {canOverride ? (
        <td className="move-cell">
          <button
            type="button"
            className="btn small ghost"
            aria-label={`${onDesk ? "Defer" : "Promote"} ${row.case_id}`}
            onClick={(event) => {
              event.stopPropagation();
              onOverride({ caseId: row.case_id, action: onDesk ? "defer" : "promote" });
            }}
          >
            {onDesk ? "Defer" : "Promote"}
          </button>
        </td>
      ) : null}
    </tr>
  );
}
