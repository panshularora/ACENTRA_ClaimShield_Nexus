import { useQuery } from "@tanstack/react-query";
import { useNavigate } from "@tanstack/react-router";
import { useState } from "react";
import { api, can } from "../../api/client";
import { useAuth } from "../../auth/AuthProvider";

export function WikiProposalsPage() {
  const { user } = useAuth();
  const navigate = useNavigate();
  const [status, setStatus] = useState("pending");
  const allowed = can(user, "wiki:read");
  const query = useQuery({
    queryKey: ["wiki-proposals", status],
    queryFn: () => api.listProposals(status === "all" ? undefined : status),
    enabled: allowed,
  });

  if (!user) return null;
  if (!allowed) {
    return (
      <main id="main" className="page">
        <h1>Precedent proposals</h1>
        <p className="error-text">Your role cannot read wiki proposals.</p>
      </main>
    );
  }

  const rows = query.data?.proposals ?? [];

  return (
    <main id="main" className="page">
      <header className="page-head">
        <div>
          <p className="kicker">Navigator-style knowledge loop</p>
          <h1>Precedent proposals</h1>
          <p className="lede">
            A human decision drafts a pending precedent. Manager or analyst approval publishes it
            so later briefs can cite it. The model never writes policy by itself.
          </p>
        </div>
        <label>
          Status
          <select value={status} onChange={(e) => setStatus(e.target.value)}>
            <option value="pending">Pending</option>
            <option value="approved">Approved</option>
            <option value="rejected">Rejected</option>
            <option value="all">All</option>
          </select>
        </label>
      </header>
      {query.isLoading && <p className="muted">Loading proposals…</p>}
      {query.error && <p className="error-text">{(query.error as Error).message}</p>}
      <div className="table-wrap">
        <table className="grid">
          <thead>
            <tr>
              <th>Proposal</th>
              <th>Source case</th>
              <th>Decision</th>
              <th>Status</th>
              <th>Created</th>
            </tr>
          </thead>
          <tbody>
            {rows.length === 0 && (
              <tr>
                <td colSpan={5} className="muted">
                  No proposals in this filter.
                </td>
              </tr>
            )}
            {rows.map((row) => (
              <tr
                key={row.proposal_id}
                onClick={() =>
                  void navigate({
                    to: "/wiki/proposals/$proposalId",
                    params: { proposalId: row.proposal_id },
                  })
                }
              >
                <td>
                  <strong>{row.title}</strong>
                  <div className="mono muted">{row.proposal_id}</div>
                </td>
                <td className="mono">{row.source_case_id}</td>
                <td>{row.body.decision ?? "—"}</td>
                <td>
                  <span className="badge">{row.status}</span>
                </td>
                <td className="mono">{row.created_at ?? "—"}</td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </main>
  );
}
