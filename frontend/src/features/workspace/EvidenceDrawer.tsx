import { useQuery } from "@tanstack/react-query";
import type { AlertLineage } from "../../api/types";
import { api } from "../../api/client";
import { PeerCompare } from "./PeerCompare";
import { AlertLineageBlock } from "./ProvenancePanel";

export function EvidenceDrawer({
  caseId,
  itemId,
  onClose,
}: {
  caseId: string;
  itemId: string;
  onClose: () => void;
}) {
  const query = useQuery({
    queryKey: ["evidence", caseId, itemId],
    queryFn: () => api.getEvidence(caseId, itemId),
  });
  const payload = query.data?.payload as Record<string, unknown> | undefined;
  const evidence =
    payload && typeof payload.evidence === "object" && payload.evidence
      ? (payload.evidence as Record<string, unknown>)
      : payload;

  return (
    <aside className="drawer evidence-drawer" role="dialog" aria-labelledby="ev-title">
      <header className="drawer-head">
        <div>
          <p className="kicker">Trace this finding</p>
          <h2 id="ev-title" className="mono">
            {itemId}
          </h2>
        </div>
        <button type="button" className="btn ghost" onClick={onClose}>
          Close
        </button>
      </header>
      {query.isLoading && <p className="muted">Loading evidence…</p>}
      {query.error && <p className="error-text">{(query.error as Error).message}</p>}
      {query.data && (
        <div className="drawer-body">
          <p>
            This panel shows the claims, fields, rule, or graph connection behind the system’s
            claim. An alert is a suspicion to verify.
          </p>
          <p className="muted">
            Kind <span className="mono">{query.data.kind}</span>
          </p>
          {payload?.lineage && typeof payload.lineage === "object" ? (
            <AlertLineageBlock lineage={payload.lineage as AlertLineage} />
          ) : null}
          {evidence?.peer_group ? <PeerCompare evidence={evidence} /> : null}
          {typeof evidence?.review_reason === "string" && <p>{evidence.review_reason}</p>}
          {typeof payload?.source_system === "string" && (
            <p className="muted">
              Claim source <span className="mono">{payload.source_system}</span>
              {payload.source_ref ? <span className="mono"> {String(payload.source_ref)}</span> : null}
            </p>
          )}
          <pre className="evidence-json">{JSON.stringify(query.data.payload, null, 2)}</pre>
        </div>
      )}
    </aside>
  );
}
