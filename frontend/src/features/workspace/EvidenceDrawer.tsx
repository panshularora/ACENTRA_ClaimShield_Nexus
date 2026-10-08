import { useQuery } from "@tanstack/react-query";
import type { AlertLineage } from "../../api/types";
import { api } from "../../api/client";
import { Drawer } from "../../components/ui/Drawer";
import { ErrorState, LoadingState } from "../../components/ui/States";
import { PeerCompare } from "./PeerCompare";
import { AlertLineageBlock } from "./ProvenancePanel";

function isRecord(value: unknown): value is Record<string, unknown> {
  return typeof value === "object" && value !== null;
}

/** Side drawer that traces one cited item (alert, line, provider) back to its stored evidence. */
export function EvidenceDrawer({ caseId, itemId, onClose }: { caseId: string; itemId: string; onClose: () => void }) {
  const query = useQuery({
    queryKey: ["evidence", caseId, itemId],
    queryFn: () => api.getEvidence(caseId, itemId),
  });
  const payload = query.data?.payload;
  const evidence = payload && isRecord(payload.evidence) ? payload.evidence : payload;

  return (
    <Drawer titleId="ev-title" eyebrow="Trace this evidence" title={<span className="mono">{itemId}</span>} onClose={onClose}>
          {query.isLoading ? <LoadingState label="Loading evidence…" /> : null}
          {query.error ? <ErrorState title="Evidence unavailable" error={query.error} /> : null}
          {query.data ? (
            <>
              <p>
                The claims, fields, rule or graph connection behind this citation. An alert is a suspicion to verify.
              </p>
              <p className="muted">
                Kind <span className="badge">{query.data.kind}</span>
              </p>
              {payload && isRecord(payload.lineage) ? (
                <AlertLineageBlock lineage={payload.lineage as unknown as AlertLineage} />
              ) : null}
              {evidence?.peer_group ? <PeerCompare evidence={evidence} /> : null}
              {typeof evidence?.review_reason === "string" ? <p>{evidence.review_reason}</p> : null}
              {typeof payload?.source_system === "string" ? (
                <p className="muted">
                  Claim source <span className="mono">{payload.source_system}</span>
                  {payload.source_ref ? <span className="mono"> {String(payload.source_ref)}</span> : null}
                </p>
              ) : null}
              <details>
                <summary>Raw payload</summary>
                <pre className="code-block">{JSON.stringify(query.data.payload, null, 2)}</pre>
              </details>
            </>
          ) : null}
    </Drawer>
  );
}
