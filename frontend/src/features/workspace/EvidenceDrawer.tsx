import { useQuery } from "@tanstack/react-query";
import { api } from "../../api/client";

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

  return (
    <aside className="drawer evidence-drawer" role="dialog" aria-labelledby="ev-title">
      <header className="drawer-head">
        <div>
          <p className="kicker">Evidence source</p>
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
          <p className="muted">
            Kind <span className="mono">{query.data.kind}</span>
          </p>
          <pre className="evidence-json">{JSON.stringify(query.data.payload, null, 2)}</pre>
        </div>
      )}
    </aside>
  );
}
