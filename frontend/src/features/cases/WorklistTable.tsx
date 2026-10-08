import { Link } from "@tanstack/react-router";
import type { CaseDetail, QueueCase } from "../../api/types";
import { HarmFlag, LaneBadge, StatusBadge } from "../../components/Badge";
import { CaseAxes } from "../../components/CaseAxes";

interface WorklistTableProps {
  rows: QueueCase[];
  details: Record<string, CaseDetail>;
  userId: string;
  canAssign: boolean;
  /** Case id whose assignment request is in flight. */
  assigning?: string;
  onAssign: (caseId: string) => void;
}

/** Investigator worklist as stacked cards with the six SIU axes. */
export function WorklistTable({ rows, details, userId, canAssign, assigning, onAssign }: WorklistTableProps) {
  return (
    <ul className="worklist-cards">
      {rows.map((row) => {
        const extra = details[row.case_id];
        const mine = extra?.assignee_id === userId;
        const group = row.alert_group;
        const name = extra?.primary_entity?.name ?? row.primary_entity_id;
        return (
          <li key={row.case_id} className={`work-card lane-${row.lane}`}>
            <div className="work-card-top">
              <div className="chip-row">
                <LaneBadge lane={row.lane} />
                <StatusBadge status={row.status} />
                <HarmFlag harm={row.harm} />
              </div>
              <span className="mono muted work-card-id">{row.case_id}</span>
            </div>
            <div className="work-card-body">
              <div className="work-card-main">
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
                {group ? (
                  <p className="muted work-card-group" title={group.text}>
                    {group.n_alerts ? `${group.n_alerts} patterns reviewed together` : "Patterns reviewed together"}
                    {group.n_entities > 1 ? ` · ${group.n_entities} linked providers` : ""}
                    {group.urgent ? " · urgent still visible" : ""}
                  </p>
                ) : null}
              </div>
              {canAssign && !mine ? (
                <button
                  type="button"
                  className="btn ghost work-card-action"
                  disabled={assigning === row.case_id}
                  aria-label={`Take ownership of ${row.case_id}`}
                  onClick={() => onAssign(row.case_id)}
                >
                  {assigning === row.case_id ? "Assigning…" : "Take ownership"}
                </button>
              ) : null}
              <CaseAxes data={extra ?? row} />
            </div>
          </li>
        );
      })}
    </ul>
  );
}
