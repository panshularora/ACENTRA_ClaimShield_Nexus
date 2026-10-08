import { Link } from "@tanstack/react-router";
import type { CaseDetail, SessionUser } from "../../api/types";
import { HarmFlag, LaneBadge, RiskBadge, StatusBadge } from "../../components/Badge";
import { EvidenceBar } from "../../components/EvidenceBar";
import { RiskHorizonChart } from "../../components/charts/RiskHorizonChart";
import { StatTile } from "../../components/ui/StatTile";
import { SCORE_LABELS } from "../../lib/scoreLabels";
import { hours, money, pct, screeningLabel, screeningTone } from "../../lib/format";

interface CaseHeaderProps {
  data: CaseDetail;
  user: SessionUser;
  canAssign: boolean;
  assigning: boolean;
  onAssign: () => void;
  unmask: boolean;
  onUnmaskChange: (value: boolean) => void;
}

/** 1 · Who is under review, how risky, and how urgent. */
export function CaseHeader({ data, user, canAssign, assigning, onAssign, unmask, onUnmaskChange }: CaseHeaderProps) {
  const subject = data.primary_entity;
  const owner = data.assignee_id === user.id ? "You" : (data.assignee_id ?? "Unassigned");
  return (
    <header className="case-header panel" aria-labelledby="case-title">
      <div className="case-header-main">
        <div className="case-identity">
          <p className="kicker">1 · Case subject · suspicion only</p>
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
            <RiskBadge severity={data.severity} />
            <HarmFlag harm={data.harm} />
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
          <a href="#decide" className="btn solid">
            Record next step
          </a>
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
        <dl className="stat-grid">
          <StatTile label={SCORE_LABELS.pConfirm.label} value={pct(data.p_confirm)} hint={SCORE_LABELS.pConfirm.hint} />
          <StatTile label="Flagged paid" value={money(data.flagged_dollars)} />
          <StatTile
            label={SCORE_LABELS.expectedValue.label}
            value={money(data.expected_value ?? 0)}
            hint={SCORE_LABELS.expectedValue.hint}
          />
          <StatTile label="Members" value={data.members_affected} tone={data.harm >= 3 ? "harm" : "default"} />
          <StatTile label="Est. hours" value={hours(data.estimated_hours)} />
          <StatTile label="Evidence" value={<EvidenceBar value={data.evidence_strength} />} />
        </dl>
        <RiskHorizonChart f30={data.f30} f60={data.f60} f90={data.f90} />
      </div>
    </header>
  );
}
