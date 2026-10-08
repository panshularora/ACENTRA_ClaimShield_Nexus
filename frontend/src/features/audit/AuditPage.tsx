import { useQuery } from "@tanstack/react-query";
import { useState } from "react";
import { api, can } from "../../api/client";
import { useAuth } from "../../auth/AuthProvider";

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
        <h1>Audit log</h1>
        <p className="error-text">Your role cannot read the audit log.</p>
      </main>
    );
  }

  const events = query.data?.events ?? [];
  const verification = query.data?.verification;

  return (
    <main id="main" className="page">
      <header className="page-head">
        <div>
          <p className="kicker">Auditor</p>
          <h1>Audit log</h1>
          <p className="lede">
            Hash-chained events. Payloads are redacted. This view never shows secrets.
          </p>
        </div>
        {verification && (
          <p className={verification.intact ? "banner ok" : "banner warn"}>
            Chain {verification.intact ? "intact" : "broken"} · last seq {verification.last_seq} ·{" "}
            {verification.n_events} events
          </p>
        )}
      </header>
      <div className="toolbar">
        <label>
          Actor
          <input value={actor} onChange={(e) => setActor(e.target.value)} placeholder="id or name" />
        </label>
        <label>
          Action
          <input value={action} onChange={(e) => setAction(e.target.value)} placeholder="case.decide" />
        </label>
      </div>
      {query.isLoading && <p className="muted">Loading audit events…</p>}
      {query.error && <p className="error-text">{(query.error as Error).message}</p>}
      <div className="table-wrap">
        <table className="grid audit-grid">
          <thead>
            <tr>
              <th>Seq</th>
              <th>Timestamp</th>
              <th>Actor</th>
              <th>Action</th>
              <th>Resource</th>
              <th>Verify</th>
            </tr>
          </thead>
          <tbody>
            {events.map((event) => (
              <tr key={event.seq}>
                <td className="mono">{event.seq}</td>
                <td className="mono">{event.ts}</td>
                <td>
                  {event.actor}
                  <div className="muted">{event.role}</div>
                </td>
                <td className="mono">{event.action}</td>
                <td className="mono">
                  {event.object_type}/{event.object_id}
                </td>
                <td>{event.chain_ok ? "ok" : "fail"}</td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </main>
  );
}
