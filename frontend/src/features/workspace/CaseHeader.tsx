import { Link } from "@tanstack/react-router";
import type { CaseDetail, RiskFactor, SessionUser } from "../../api/types";
import { CaseAxes } from "../../components/CaseAxes";
import { LaneBadge, StatusBadge } from "../../components/Badge";
import { RiskHorizonChart } from "../../components/charts/RiskHorizonChart";
import { SCORE_LABELS } from "../../lib/scoreLabels";
import { screeningLabel, screeningTone } from "../../lib/format";

interface CaseHeaderProps {
  data: CaseDetail;
  user: SessionUser;
  canAssign: boolean;
  assigning: boolean;
  onAssign: () => void;
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
  onAssign,
  onDecide,
  unmask,
  onUnmaskChange,
}: CaseHeaderProps) {
  const subject = data.primary_entity;
  const owner = data.assignee_id === user.id ? "You" : (data.assignee_id ?? "Unassigned");
  const scorer =
    data.score_kind === "trained_model"
      ? data.calibrated
        ? "Learned score · adjusted"
        : "Learned score"
      : data.score_kind === "uncalibrated_heuristic"
        ? "Simple score"
        : null;
  return (
    <header className="case-header panel" aria-labelledby="case-title">
      <div className="case-header-main">
        <div className="case-identity">
          <p className="kicker">
            Case subject · {data.primary_entity_type === "member" ? "member" : "provider"} · suspicion only
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
            {scorer ? (
              <span className="badge" title={SCORE_LABELS.pConfirm.hintFor(data)}>
                {scorer}
                {data.model_version ? ` · ${data.model_version}` : ""}
              </span>
            ) : null}
            <span className={`sla-chip sla-${screeningTone(data.screening_days_left)}`}>
              {screeningLabel(data.screening_days_left)}
            </span>
            {data.provenance && data.provenance.urgent.length > 0 ? (
              <span className="badge tone-danger">Urgent signal in group</span>
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
        <RiskHorizonChart f30={data.f30} f60={data.f60} f90={data.f90} />
      </div>
    </header>
  );
}

export function FactorList({ title, factors }: { title: string; factors?: RiskFactor[] }) {
  if (!factors || factors.length === 0) return null;
  const top = [...factors].sort((a, b) => Math.abs(b.contribution) - Math.abs(a.contribution)).slice(0, 5);
  return (
    <div className="subpanel">
      <h3>{title}</h3>
      <ul className="factor-contrib">
        {top.map((factor) => (
          <li key={factor.feature}>
            <span>{factor.label}</span>
            <span className={`num ${factor.direction === "raises" ? "up" : "down"}`}>
              {factor.direction === "raises" ? "+" : "−"}
              {Math.abs(factor.contribution).toFixed(2)}
            </span>
          </li>
        ))}
      </ul>
    </div>
  );
}
