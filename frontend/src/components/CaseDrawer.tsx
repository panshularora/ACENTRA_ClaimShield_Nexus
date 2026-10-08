import { useQuery } from "@tanstack/react-query";
import { Link } from "@tanstack/react-router";
import { api } from "../api/client";
import { hours, money, pct, signalLabel, whyPriority } from "../lib/format";
import { EvidenceBar } from "./EvidenceBar";
import { HarmBadge, LaneBadge, StatusBadge } from "./Badge";

export function CaseDrawer({
  caseId,
  onClose,
}: {
  caseId: string;
  onClose: () => void;
  openHref?: string;
}) {
  const query = useQuery({
    queryKey: ["case", caseId],
    queryFn: () => api.getCase(caseId),
  });

  return (
    <aside className="drawer" role="dialog" aria-labelledby="case-drawer-title">
      <header className="drawer-head">
        <div>
          <p className="kicker">Case file</p>
          <h2 id="case-drawer-title" className="mono">
            {caseId}
          </h2>
        </div>
        <button type="button" className="btn ghost" onClick={onClose}>
          Close
        </button>
      </header>
      {query.isLoading && <p className="muted">Loading case…</p>}
      {query.error && <p className="error-text">{(query.error as Error).message}</p>}
      {query.data && (
        <div className="drawer-body">
          <div className="chip-row">
            <LaneBadge lane={query.data.lane} />
            <StatusBadge status={query.data.status} />
            <HarmBadge harm={query.data.harm} />
          </div>
          <dl className="facts">
            <div>
              <dt>Primary entity</dt>
              <dd className="mono">{query.data.primary_entity_id}</dd>
            </div>
            <div>
              <dt>Type</dt>
              <dd>{query.data.primary_entity_type}</dd>
            </div>
            <div>
              <dt>Flagged</dt>
              <dd className="mono">{money(query.data.flagged_dollars)}</dd>
            </div>
            <div>
              <dt>Members</dt>
              <dd className="mono">{query.data.members_affected}</dd>
            </div>
            <div>
              <dt>P(confirm)</dt>
              <dd className="mono">{pct(query.data.p_confirm)}</dd>
            </div>
            <div>
              <dt>Hours</dt>
              <dd className="mono">{hours(query.data.estimated_hours)}</dd>
            </div>
            <div>
              <dt>F30 / F60 / F90</dt>
              <dd className="mono">
                {pct(query.data.f30)} · {pct(query.data.f60)} · {pct(query.data.f90)}
              </dd>
            </div>
            <div>
              <dt>Assignee</dt>
              <dd className="mono">{query.data.assignee_id ?? "Unassigned"}</dd>
            </div>
            <div>
              <dt>Why this lane</dt>
              <dd>{whyPriority(query.data)}</dd>
            </div>
          </dl>
          <div>
            <p className="kicker">Evidence strength</p>
            <EvidenceBar value={query.data.evidence_strength} />
          </div>
          <div>
            <p className="kicker">Signals on this case</p>
            {query.data.alerts.length === 0 ? (
              <p className="muted">No alerts attached.</p>
            ) : (
              <ul className="signal-list">
                {query.data.alerts.map((alert) => (
                  <li key={alert.alert_id}>
                    <span className="mono">{alert.rule_id ?? alert.detector}</span>
                    <span>{signalLabel(alert.evidence)}</span>
                    <span className="muted">{alert.line_ids.length} lines</span>
                  </li>
                ))}
              </ul>
            )}
          </div>
          <Link
            to="/investigator/workspace/$caseId"
            params={{ caseId }}
            className="btn solid"
          >
            Open investigation workspace
          </Link>
        </div>
      )}
    </aside>
  );
}
