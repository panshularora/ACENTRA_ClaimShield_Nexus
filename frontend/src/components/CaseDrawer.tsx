import { useQuery } from "@tanstack/react-query";
import { Link } from "@tanstack/react-router";
import { api } from "../api/client";
import { hours, money, pct, screeningLabel, signalLabel, whyPriority } from "../lib/format";
import { ConfirmBandBadge, HarmFlag, LaneBadge, RiskBadge, StatusBadge } from "./Badge";
import { EvidenceBar } from "./EvidenceBar";
import { Drawer } from "./ui/Drawer";
import { SCORE_LABELS } from "../lib/scoreLabels";
import { ErrorState, LoadingState } from "./ui/States";

/** Quick case summary opened from the manager queue. */
export function CaseDrawer({ caseId, onClose }: { caseId: string; onClose: () => void }) {
  const query = useQuery({
    queryKey: ["case", caseId],
    queryFn: () => api.getCase(caseId),
  });
  const detail = query.data;

  return (
    <Drawer
      titleId="case-drawer-title"
      eyebrow="Case file"
      title={detail?.primary_entity?.name ?? caseId}
      subtitle={caseId}
      onClose={onClose}
    >
      {query.isLoading ? <LoadingState label="Loading case…" /> : null}
      {query.error ? <ErrorState title="Case unavailable" error={query.error} /> : null}
      {detail ? (
        <>
          <div className="chip-row">
            <LaneBadge lane={detail.lane} />
            <StatusBadge status={detail.status} />
            <RiskBadge severity={detail.severity} />
            <HarmFlag harm={detail.harm} />
            <ConfirmBandBadge p={detail.p_confirm} />
          </div>
          {detail.model_version ? (
            <p className="muted">
              {SCORE_LABELS.pConfirm.hintFor(detail)}
              {detail.model_version ? ` · ${detail.model_version}` : ""}
            </p>
          ) : null}
          <p>{whyPriority(detail)}</p>
          <dl className="facts">
            <div>
              <dt>Primary entity</dt>
              <dd className="mono">{detail.primary_entity_id}</dd>
            </div>
            <div>
              <dt>Type</dt>
              <dd>{detail.primary_entity_type}</dd>
            </div>
            <div>
              <dt>Flagged</dt>
              <dd className="num">{money(detail.flagged_dollars)}</dd>
            </div>
            <div>
              <dt>Members</dt>
              <dd className="num">{detail.members_affected}</dd>
            </div>
            <div>
              <dt>{SCORE_LABELS.pConfirm.label}</dt>
              <dd className="num">{pct(detail.p_confirm)}</dd>
            </div>
            <div>
              <dt>Hours</dt>
              <dd className="num">{hours(detail.estimated_hours)}</dd>
            </div>
            <div>
              <dt>{SCORE_LABELS.horizon.shortSet}</dt>
              <dd className="num">
                {pct(detail.f30)} · {pct(detail.f60)} · {pct(detail.f90)}
              </dd>
            </div>
            <div>
              <dt>Assignee</dt>
              <dd className="mono">{detail.assignee_id ?? "Unassigned"}</dd>
            </div>
            <div>
              <dt>45-day screen</dt>
              <dd>{screeningLabel(detail.screening_days_left)}</dd>
            </div>
          </dl>
          <div>
            <p className="kicker">Evidence strength</p>
            <EvidenceBar value={detail.evidence_strength} />
          </div>
          <div>
            <p className="kicker">Signals on this case</p>
            {detail.alerts.length === 0 ? (
              <p className="muted">No alerts attached.</p>
            ) : (
              <ul className="compact-list signal-list">
                {detail.alerts.map((alert) => (
                  <li key={alert.alert_id}>
                    <span className="mono">{alert.rule_id ?? alert.detector}</span> {signalLabel(alert.evidence)}{" "}
                    <span className="muted">· {alert.line_ids.length} lines</span>
                  </li>
                ))}
              </ul>
            )}
          </div>
          <Link to="/investigator/workspace/$caseId" params={{ caseId }} className="btn solid">
            Open investigation workspace
          </Link>
        </>
      ) : null}
    </Drawer>
  );
}
