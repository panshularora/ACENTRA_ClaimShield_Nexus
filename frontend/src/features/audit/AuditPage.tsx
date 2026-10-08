import { useQuery } from "@tanstack/react-query";
import { useState } from "react";
import { api, can } from "../../api/client";
import { useAuth } from "../../auth/AuthProvider";
import { PageHeader } from "../../components/ui/PageHeader";
import { Panel } from "../../components/ui/Panel";
import { EmptyState, ErrorState, LoadingState } from "../../components/ui/States";
import { dateTime } from "../../lib/format";

export function AuditPage() {
  const { user } = useAuth();
  const [actor, setActor] = useState("");
  const [action, setAction] = useState("");
  const allowed = can(user, "audit:read");
  const query = useQuery({
    queryKey: ["audit", actor, action],
    queryFn: () =>
      api.getAudit({
        actor: actor.trim() || undefined,
        action: action.trim() || undefined,
      }),
    enabled: allowed,
  });

  if (!user) return null;
  if (!allowed) {
    return (
      <main id="main" className="page">
        <PageHeader eyebrow="Auditor" title="Audit log" />
        <ErrorState title="Access denied" error="Your role cannot read the audit log." />
      </main>
    );
  }

  const events = query.data?.events ?? [];
  const verification = query.data?.verification;

  return (
    <main id="main" className="page">
      <PageHeader
        eyebrow="Auditor"
        title="Audit log"
        description="Every load, run, unmask and decision appends to a hash chain. Payloads are redacted; this view never shows secrets."
        actions={
          verification ? (
            <p className={`banner ${verification.intact ? "ok" : "warn"}`} role="status">
              Chain {verification.intact ? "intact" : "broken"} · last seq {verification.last_seq} ·{" "}
              {verification.n_events} events
            </p>
          ) : null
        }
      />
      <Panel id="audit-events" eyebrow="Events" title="Chain entries" actions={<span className="badge">{events.length} shown</span>}>
        <div className="toolbar">
          <label className="field">
            Actor
            <input value={actor} onChange={(e) => setActor(e.target.value)} placeholder="ID or name" />
          </label>
          <label className="field">
            Action
            <input value={action} onChange={(e) => setAction(e.target.value)} placeholder="case.decide" />
          </label>
        </div>
        {query.isLoading ? <LoadingState label="Loading audit events…" /> : null}
        {query.error ? <ErrorState title="Audit log unavailable" error={query.error} /> : null}
        {query.data && events.length === 0 ? (
          <EmptyState title="No events match" compact>
            Clear the actor or action filter.
          </EmptyState>
        ) : null}
        {events.length > 0 ? (
          <div className="table-wrap">
            <table className="grid">
              <caption className="sr-only">Audit chain events, newest last</caption>
              <thead>
                <tr>
                  <th scope="col" className="num">
                    Seq
                  </th>
                  <th scope="col">Time</th>
                  <th scope="col">Actor</th>
                  <th scope="col">Action</th>
                  <th scope="col">Resource</th>
                  <th scope="col">Chain check</th>
                </tr>
              </thead>
              <tbody>
                {events.map((event) => (
                  <tr key={event.seq}>
                    <td className="num">{event.seq}</td>
                    <td>
                      <time dateTime={event.ts}>{dateTime(event.ts)}</time>
                    </td>
                    <td>
                      {event.actor}
                      <span className="muted"> · {event.role}</span>
                    </td>
                    <td className="mono">{event.action}</td>
                    <td className="mono">
                      {event.object_type}/{event.object_id}
                    </td>
                    <td>
                      <span className={`badge ${event.chain_ok ? "tone-ok" : "tone-danger"}`}>
                        {event.chain_ok ? "Verified" : "Failed"}
                      </span>
                    </td>
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
