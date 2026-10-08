import { useQuery } from "@tanstack/react-query";
import { Link } from "@tanstack/react-router";
import { useState } from "react";
import { api, can } from "../../api/client";
import { useAuth } from "../../auth/AuthProvider";
import { PageHeader } from "../../components/ui/PageHeader";
import { Panel } from "../../components/ui/Panel";
import { EmptyState, ErrorState, LoadingState } from "../../components/ui/States";
import { dateTime, humanize } from "../../lib/format";

const STATUSES = ["pending", "approved", "rejected", "all"] as const;
type StatusFilter = (typeof STATUSES)[number];

export function WikiProposalsPage() {
  const { user } = useAuth();
  const [status, setStatus] = useState<StatusFilter>("pending");
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
        <PageHeader eyebrow="Knowledge loop" title="Precedent proposals" />
        <ErrorState title="Access denied" error="Your role cannot read wiki proposals." />
      </main>
    );
  }

  const rows = query.data?.proposals ?? [];

  return (
    <main id="main" className="page">
      <PageHeader
        eyebrow="Knowledge loop"
        title="Precedent proposals"
        description="A human decision drafts a pending precedent. Manager or analyst approval publishes it so later briefs can cite it. The model never writes policy by itself."
      />
      <Panel
        id="proposals"
        eyebrow="Review queue"
        title={`${humanize(status)} proposals`}
        actions={
          <div className="segmented" role="group" aria-label="Filter by status">
            {STATUSES.map((value) => (
              <button key={value} type="button" aria-pressed={status === value} onClick={() => setStatus(value)}>
                {humanize(value)}
              </button>
            ))}
          </div>
        }
      >
        {query.isLoading ? <LoadingState label="Loading proposals…" /> : null}
        {query.error ? <ErrorState title="Proposals unavailable" error={query.error} /> : null}
        {query.data && rows.length === 0 ? (
          <EmptyState title="No proposals in this filter" compact>
            Decisions recorded in a case workspace draft new proposals here.
          </EmptyState>
        ) : null}
        {rows.length > 0 ? (
          <div className="table-wrap">
            <table className="grid">
              <caption className="sr-only">Precedent proposals</caption>
              <thead>
                <tr>
                  <th scope="col">Proposal</th>
                  <th scope="col">Source case</th>
                  <th scope="col">Decision</th>
                  <th scope="col">Status</th>
                  <th scope="col">Created</th>
                </tr>
              </thead>
              <tbody>
                {rows.map((row) => (
                  <tr key={row.proposal_id}>
                    <th scope="row">
                      <Link
                        to="/wiki/proposals/$proposalId"
                        params={{ proposalId: row.proposal_id }}
                        className="row-title"
                      >
                        {row.title}
                      </Link>
                      <span className="mono muted"> {row.proposal_id}</span>
                    </th>
                    <td>
                      <Link
                        to="/investigator/workspace/$caseId"
                        params={{ caseId: row.source_case_id }}
                        className="mono"
                      >
                        {row.source_case_id}
                      </Link>
                    </td>
                    <td>{row.body.decision ? humanize(row.body.decision) : "—"}</td>
                    <td>
                      <span className="badge">{humanize(row.status)}</span>
                    </td>
                    <td>{dateTime(row.created_at)}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        ) : null}
      </Panel>
    </main>
  );
}
