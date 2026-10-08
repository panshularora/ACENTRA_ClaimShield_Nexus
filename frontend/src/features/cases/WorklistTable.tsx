import { Link } from "@tanstack/react-router";
import type { CaseDetail, QueueCase } from "../../api/types";
import { HarmFlag, LaneBadge, RiskBadge, StatusBadge } from "../../components/Badge";
import { EvidenceBar } from "../../components/EvidenceBar";
import { hours, money, pct } from "../../lib/format";
import { SCORE_LABELS } from "../../lib/scoreLabels";

interface WorklistTableProps {
  rows: QueueCase[];
  details: Record<string, CaseDetail>;
  userId: string;
  canAssign: boolean;
  /** Case id whose assignment request is in flight. */
  assigning?: string;
  onAssign: (caseId: string) => void;
}

/** Investigator worklist. A table on wide screens; each row stacks into a card below 720px. */
export function WorklistTable({ rows, details, userId, canAssign, assigning, onAssign }: WorklistTableProps) {
  return (
    <div className="table-wrap worklist-wrap">
      <table className="grid worklist">
        <caption className="sr-only">Cases on the investigator desk</caption>
        <thead>
          <tr>
            <th scope="col">Case subject</th>
            <th scope="col">Lane</th>
            <th scope="col">Risk</th>
            <th scope="col">Harm</th>
            <th scope="col" className="num">
              {SCORE_LABELS.pConfirm.label}
            </th>
            <th scope="col" className="num">
              {SCORE_LABELS.horizon.shortSet}
            </th>
            <th scope="col" className="num">
              Flagged
            </th>
            <th scope="col" className="num">
              Hours
            </th>
            <th scope="col">Evidence</th>
            <th scope="col">Owner</th>
            {canAssign ? (
              <th scope="col">
                <span className="sr-only">Actions</span>
              </th>
            ) : null}
          </tr>
        </thead>
        <tbody>
          {rows.map((row) => {
            const extra = details[row.case_id];
            const mine = extra?.assignee_id === userId;
            const group = row.alert_group;
            return (
              <tr key={row.case_id} className={`lane-${row.lane}`}>
                <th scope="row" className="subject-cell">
                  <Link to="/investigator/workspace/$caseId" params={{ caseId: row.case_id }} className="row-title">
                    {extra?.primary_entity?.name ?? row.primary_entity_id}
                  </Link>
                  <span className="muted">
                    <span className="mono">{row.case_id}</span> · <span className="mono">{row.primary_entity_id}</span>
                    {extra?.primary_entity?.specialty ? ` · ${extra.primary_entity.specialty}` : ""}
                  </span>
                  {group ? (
                    <span className="muted" title={group.text}>
                      {group.n_alerts ? `${group.n_alerts} grouped alerts` : "Grouped alerts"}
                      {group.n_entities > 1 ? ` · ${group.n_entities} linked NPIs` : ""}
                    </span>
                  ) : null}
                  <StatusBadge status={row.status} />
                </th>
                <td data-label="Lane">
                  <LaneBadge lane={row.lane} />
                </td>
                <td data-label="Risk">
                  <RiskBadge severity={row.severity} />
                </td>
                <td data-label="Harm">
                  <HarmFlag harm={row.harm} />
                </td>
                <td className="num" data-label={SCORE_LABELS.pConfirm.label}>
                  {pct(row.p_confirm)}
                </td>
                <td className="num" data-label={SCORE_LABELS.horizon.shortSet}>
                  {pct(row.f30)} · {pct(row.f60)} · {pct(row.f90)}
                </td>
                <td className="num dollars" data-label="Flagged">
                  {money(row.flagged_dollars)}
                </td>
                <td className="num" data-label="Hours">
                  {hours(row.estimated_hours)}
                </td>
                <td data-label="Evidence">
                  <EvidenceBar value={row.evidence_strength} />
                </td>
                <td data-label="Owner">{mine ? "You" : (extra?.assignee_id ?? <span className="muted">Unassigned</span>)}</td>
                {canAssign ? (
                  <td className="action-cell">
                    {!mine ? (
                      <button
                        type="button"
                        className="btn small ghost"
                        disabled={assigning === row.case_id}
                        aria-label={`Take ownership of ${row.case_id}`}
                        onClick={() => onAssign(row.case_id)}
                      >
                        {assigning === row.case_id ? "Assigning…" : "Take ownership"}
                      </button>
                    ) : null}
                  </td>
                ) : null}
              </tr>
            );
          })}
        </tbody>
      </table>
    </div>
  );
}
