import { useQuery } from "@tanstack/react-query";
import { Link } from "@tanstack/react-router";
import { api } from "../api/client";
import { alertLabel, whyPriority } from "../lib/format";
import { findingCopy } from "../lib/plainLanguage";
import { CaseAxes } from "./CaseAxes";
import { LaneBadge, StatusBadge } from "./Badge";
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
          </div>
          {detail.model_version ? (
            <p className="muted">
              {SCORE_LABELS.pConfirm.hintFor(detail)}
              {detail.model_version ? ` · ${detail.model_version}` : ""}
            </p>
          ) : null}
          <p>{whyPriority(detail)}</p>
          <CaseAxes data={detail} />
          <p className="muted">
            Owner {detail.assignee_id ?? "Unassigned"} · {detail.primary_entity_type} {detail.primary_entity_id}
          </p>
          <div>
            <p className="kicker">What we noticed</p>
            {detail.alerts.length === 0 ? (
              <p className="muted">No patterns attached.</p>
            ) : (
              <ul className="compact-list signal-list">
                {detail.alerts.map((alert) => {
                  const kind = typeof alert.evidence?.kind === "string" ? alert.evidence.kind : alert.kind;
                  const copy = findingCopy(kind, alertLabel(alert));
                  return (
                    <li key={alert.alert_id}>
                      {copy.title}{" "}
                      <span className="muted">
                        · {alert.line_ids.length} paid claim line{alert.line_ids.length === 1 ? "" : "s"}
                      </span>
                    </li>
                  );
                })}
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
