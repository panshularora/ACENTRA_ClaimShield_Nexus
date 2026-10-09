import { Link } from "@tanstack/react-router";
import type { CaseDetail, QueueCase } from "../../api/types";
import { LaneBadge, StatusBadge } from "../../components/Badge";
import { money, pct, pctNumber, screeningShort } from "../../lib/format";

interface WorklistTableProps {
  rows: QueueCase[];
  details: Record<string, CaseDetail>;
  userId: string;
  canAssign: boolean;
  /** Case id whose assignment request is in flight. */
  assigning?: string;
  onAssign: (caseId: string) => void;
}

/** Investigator worklist as a claims-style table. Same fields as before. */
export function WorklistTable({ rows, details, userId, canAssign, assigning, onAssign }: WorklistTableProps) {
  return (
    <div className="table-wrap work-wrap">
      <table className="grid work-grid">
        <caption className="sr-only">Desk cases with provider, amount, suspicion and status</caption>
        <thead>
          <tr>
            <th scope="col">Provider</th>
            <th scope="col">Case</th>
            <th scope="col" className="num">
              Amount
            </th>
            <th scope="col">Suspicion</th>
            <th scope="col">Status</th>
            <th scope="col">
              <span className="sr-only">Actions</span>
            </th>
          </tr>
        </thead>
        <tbody>
          {rows.map((row) => {
            const extra = details[row.case_id];
            const mine = extra?.assignee_id === userId;
            const group = row.alert_group;
            const name = extra?.primary_entity?.name ?? row.primary_entity_id;
            const suspicion = pctNumber(row.p_confirm) ?? 0;
            return (
              <tr key={row.case_id} className={`lane-${row.lane}`}>
                <th scope="row">
                  <Link to="/investigator/workspace/$caseId" params={{ caseId: row.case_id }} className="work-card-name">
                    {name}
                  </Link>
                  <p className="work-card-meta">
                    <span className="mono">{row.primary_entity_id}</span>
                    {extra?.primary_entity?.specialty ? (
                      <span>{extra.primary_entity.specialty.replaceAll("_", " ")}</span>
                    ) : null}
                    <span>Owner {mine ? "You" : (extra?.assignee_id ?? "Unassigned")}</span>
                  </p>
                  <p className="work-card-scores">
                    <span>{row.severity}/4 severity</span>
                    <span>
                      {row.members_affected} people · harm {row.harm}
                    </span>
                    <span>{screeningShort(row.screening_days_left)}</span>
                    {group ? (
                      <span title={group.text}>
                        {group.n_alerts ? `${group.n_alerts} patterns` : "Grouped"}
                        {group.n_entities > 1 ? ` · ${group.n_entities} linked` : ""}
                      </span>
                    ) : null}
                  </p>
                </th>
                <td>
                  <span className="mono">{row.case_id}</span>
                  <div className="chip-row">
                    <LaneBadge lane={row.lane} />
                  </div>
                </td>
                <td className="num">{money(row.flagged_dollars)}</td>
                <td>
                  <span className="risk-cell">
                    <span className="risk-n">{pct(row.p_confirm)}</span>
                    <span className="risk-track" aria-hidden="true">
                      <i style={{ width: `${suspicion}%` }} />
                    </span>
                  </span>
                </td>
                <td>
                  <StatusBadge status={row.status} />
                </td>
                <td>
                  {canAssign && !mine ? (
                    <button
                      type="button"
                      className="btn small ghost"
                      disabled={assigning === row.case_id}
                      aria-label={`Take ownership of ${row.case_id}`}
                      onClick={() => onAssign(row.case_id)}
                    >
                      {assigning === row.case_id ? "Assigning…" : "Take"}
                    </button>
                  ) : null}
                </td>
              </tr>
            );
          })}
        </tbody>
      </table>
    </div>
  );
}
