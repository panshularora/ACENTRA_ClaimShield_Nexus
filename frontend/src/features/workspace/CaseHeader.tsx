import { Link } from "@tanstack/react-router";
import type { CaseDetail, SessionUser } from "../../api/types";
import { CaseAxes } from "../../components/CaseAxes";
import { LaneBadge, StatusBadge } from "../../components/Badge";
import { RiskHorizonChart } from "../../components/charts/RiskHorizonChart";

interface CaseHeaderProps {
  data: CaseDetail;
  user: SessionUser;
  canAssign: boolean;
  assigning: boolean;
  unassigning: boolean;
  onAssign: () => void;
  onUnassign: () => void;
  onDecide: () => void;
  unmask: boolean;
  onUnmaskChange: (value: boolean) => void;
}

/** Who is under review. Stays on screen while the rest of the file is tabbed. */
export function CaseHeader({
  data,
  user,
  canAssign,
  assigning,
  unassigning,
  onAssign,
  onUnassign,
  onDecide,
  unmask,
  onUnmaskChange,
}: CaseHeaderProps) {
  const subject = data.primary_entity;
  const owner = data.assignee_id === user.id ? "You" : (data.assignee_id ?? "Unassigned");
  return (
    <header className="case-header panel" aria-labelledby="case-title">
      <div className="case-header-main">
        <div className="case-identity">
          <p className="kicker">
            {data.primary_entity_type === "member" ? "Member" : "Provider"} under review
          </p>
          <h1 id="case-title">{subject?.name ?? data.primary_entity_id}</h1>
          <p className="case-ids">
            <span className="mono">{data.case_id}</span>
            <span className="mono">{data.primary_entity_id}</span>
            {subject?.npi_syn ? <span className="mono">NPI {subject.npi_syn}</span> : null}
            {subject?.specialty ? <span>{subject.specialty.replaceAll("_", " ")}</span> : null}
            {subject?.kind ? <span>{subject.kind}</span> : null}
          </p>
          <div className="chip-row">
            <LaneBadge lane={data.lane} />
            <StatusBadge status={data.status} />
            {data.provenance && data.provenance.urgent.length > 0 ? (
              <span className="badge tone-danger">Urgent in group</span>
            ) : null}
            <span className="badge">Owner: {owner}</span>
          </div>
        </div>
        <div className="case-actions">
          <Link to="/investigator/cases" className="btn ghost">
            ← Worklist
          </Link>
          {canAssign && data.assignee_id !== user.id ? (
            <button type="button" className="btn" disabled={assigning} onClick={onAssign}>
              {assigning ? "Taking…" : "Take ownership"}
            </button>
          ) : null}
          {canAssign && data.assignee_id === user.id ? (
            <button type="button" className="btn ghost" disabled={unassigning} onClick={onUnassign}>
              {unassigning ? "Releasing…" : "Release ownership"}
            </button>
          ) : null}
          <button type="button" className="btn solid" onClick={onDecide}>
            Record next step
          </button>
          {data.member_unmask_permitted ? (
            <label className="unmask-toggle">
              <input type="checkbox" checked={unmask} onChange={(event) => onUnmaskChange(event.target.checked)} />
              Reveal member names <span className="muted">(audit-logged)</span>
            </label>
          ) : (
            <p className="muted unmask-note">Member names masked: you are not assigned to this case.</p>
          )}
        </div>
      </div>
      <div className="case-header-metrics">
        <CaseAxes data={data} />
        <details className="horizon-fold">
          <summary>30 / 60 / 90-day suspicion</summary>
          <RiskHorizonChart f30={data.f30} f60={data.f60} f90={data.f90} />
        </details>
      </div>
    </header>
  );
}
