import { Link, useNavigate } from "@tanstack/react-router";
import type { CaseDetail, QueueCase } from "../../api/types";
import { HarmFlag, LaneBadge, StatusBadge } from "../../components/Badge";
import { money, pct, pctNumber, screeningLabel, screeningTone } from "../../lib/format";
import "../queue/queue.css";

interface WorklistTableProps {
  rows: QueueCase[];
  details: Record<string, CaseDetail>;
  userId: string;
  canAssign: boolean;
  /** Case id whose assignment request is in flight. */
  assigning?: string;
  /** Case id whose release request is in flight. */
  unassigning?: string;
  onAssign: (caseId: string) => void;
  onUnassign: (caseId: string) => void;
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

/** Investigator worklist as a compact ranked table, same visual language as the manager queue. */
export function WorklistTable({
  rows,
  details,
  userId,
  canAssign,
  assigning,
  unassigning,
  onAssign,
  onUnassign,
}: WorklistTableProps) {
  const navigate = useNavigate();
  return (
    <div className="table-wrap work-wrap">
      <table className="grid queue-grid work-grid">
        <caption className="sr-only">Desk cases with provider, amount, suspicion and status</caption>
        <colgroup>
          <col className="col-provider" />
          <col className="col-case" />
          <col className="col-lane" />
          <col className="col-status" />
          <col className="col-clock" />
          <col className="col-money" />
          <col className="col-suspicion" />
          <col className="col-harm" />
          <col className="col-move" />
        </colgroup>
        <thead>
          <tr>
            <th scope="col">Provider</th>
            <th scope="col">Case</th>
            <th scope="col">Lane</th>
            <th scope="col">Status</th>
            <th scope="col">45-day</th>
            <th scope="col" className="num">
              Exposure
            </th>
            <th scope="col">Suspicion</th>
            <th scope="col">Harm</th>
            <th scope="col">
              <span className="sr-only">Actions</span>
            </th>
          </tr>
        </thead>
        <tbody>
          {rows.map((row) => {
            const extra = details[row.case_id];
            const mine = extra?.assignee_id === userId;
            const name = extra?.primary_entity?.name ?? row.primary_entity_id;
            const suspicion = pctNumber(row.p_confirm) ?? 0;
            const grouped = groupLine(row);
            return (
              <tr
                key={row.case_id}
                className={`lane-${row.lane} is-clickable`}
                tabIndex={0}
                onClick={() =>
                  void navigate({ to: "/investigator/workspace/$caseId", params: { caseId: row.case_id } })
                }
                onKeyDown={(event) => {
                  if (event.key === "Enter" || event.key === " ") {
                    event.preventDefault();
                    void navigate({ to: "/investigator/workspace/$caseId", params: { caseId: row.case_id } });
                  }
                }}
              >
                <th scope="row" className="case-cell">
                  <Link
                    to="/investigator/workspace/$caseId"
                    params={{ caseId: row.case_id }}
                    className="work-card-name"
                    onClick={(event) => event.stopPropagation()}
                  >
                    {name}
                  </Link>
                  <span className="mono muted">{row.primary_entity_id}</span>
                  {grouped ? (
                    <span className="muted case-group" title={row.alert_group?.text}>
                      {grouped}
                    </span>
                  ) : null}
                </th>
                <td>
                  <Link
                    to="/investigator/workspace/$caseId"
                    params={{ caseId: row.case_id }}
                    className="link-button mono"
                    onClick={(event) => event.stopPropagation()}
                  >
                    {row.case_id}
                  </Link>
                </td>
                <td>
                  <LaneBadge lane={row.lane} />
                </td>
                <td>
                  <StatusBadge status={row.status} />
                </td>
                <td className="num">
                  <span
                    className={`sla-chip sla-${screeningTone(row.screening_days_left)}`}
                    title={screeningLabel(row.screening_days_left)}
                  >
                    {clockChip(row.screening_days_left)}
                  </span>
                </td>
                <td className="num dollars">{money(row.flagged_dollars)}</td>
                <td>
                  <span className="risk-cell">
                    <span className="risk-n">{pct(row.p_confirm)}</span>
                    <span className="risk-track" aria-hidden="true">
                      <i style={{ width: `${suspicion}%` }} />
                    </span>
                  </span>
                </td>
                <td>
                  <HarmFlag harm={row.harm} />
                </td>
                <td className="move-cell">
                  {canAssign && !mine ? (
                    <button
                      type="button"
                      className="btn small ghost"
                      disabled={assigning === row.case_id}
                      aria-label={`Take ownership of ${row.case_id}`}
                      onClick={(event) => {
                        event.stopPropagation();
                        onAssign(row.case_id);
                      }}
                    >
                      {assigning === row.case_id ? "Assigning…" : "Take"}
                    </button>
                  ) : canAssign && mine ? (
                    <button
                      type="button"
                      className="btn small ghost"
                      disabled={unassigning === row.case_id}
                      aria-label={`Release ownership of ${row.case_id}`}
                      onClick={(event) => {
                        event.stopPropagation();
                        onUnassign(row.case_id);
                      }}
                    >
                      {unassigning === row.case_id ? "Releasing…" : "Release"}
                    </button>
                  ) : mine ? (
                    <span className="muted">Yours</span>
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
