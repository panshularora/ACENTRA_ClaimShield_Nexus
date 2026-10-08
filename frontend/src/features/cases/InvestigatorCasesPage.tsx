import { useQuery } from "@tanstack/react-query";
import { useNavigate } from "@tanstack/react-router";
import { useMemo, useState } from "react";
import { api, can } from "../../api/client";
import type { CaseDetail, QueueCase } from "../../api/types";
import { useAuth } from "../../auth/AuthProvider";
import { EvidenceBar } from "../../components/EvidenceBar";
import { HarmBadge, LaneBadge, StatusBadge } from "../../components/Badge";
import { hours, money, pct } from "../../lib/format";
import { readStoredRun } from "../../lib/runStore";

export function InvestigatorCasesPage() {
  const { user } = useAuth();
  const navigate = useNavigate();
  const [queryText, setQueryText] = useState("");
  const [statusFilter, setStatusFilter] = useState("all");

  const stored = readStoredRun();
  const canCases = can(user, "case:read");
  const canQueue = can(user, "queue:read");
  const canReadBatches = can(user, "batch:read");

  const batchesQuery = useQuery({
    queryKey: ["batches"],
    queryFn: api.listBatches,
    enabled: canReadBatches,
    retry: false,
  });
  const batchId = batchesQuery.data?.[0]?.batch_id;
  const batchQuery = useQuery({
    queryKey: ["batch", batchId],
    queryFn: () => api.getBatch(batchId!),
    enabled: Boolean(batchId),
  });
  const runId = batchQuery.data?.runs[0]?.run_id ?? stored?.runId ?? null;

  const queueQuery = useQuery({
    queryKey: ["queue", runId],
    queryFn: () => api.getQueue(runId!),
    enabled: Boolean(runId) && canQueue,
  });

  const workSeed = useMemo(() => {
    const rows = queueQuery.data ?? [];
    return rows.filter((r) => r.lane === "harm_priority" || r.lane === "selected");
  }, [queueQuery.data]);

  const detailsQuery = useQuery({
    queryKey: ["work-details", runId, workSeed.map((r) => r.case_id)],
    queryFn: async () => {
      const details = await Promise.all(workSeed.map((row) => api.getCase(row.case_id)));
      return Object.fromEntries(details.map((d) => [d.case_id, d])) as Record<string, CaseDetail>;
    },
    enabled: workSeed.length > 0 && canCases,
  });

  if (!user) return null;
  if (!canCases) {
    return (
      <main id="main" className="page">
        <h1>My cases</h1>
        <p className="error-text">Your role cannot read cases.</p>
      </main>
    );
  }

  const details = detailsQuery.data ?? {};
  const assigned = workSeed.filter((row) => details[row.case_id]?.assignee_id === user.id);
  const usingAssigned = assigned.length > 0;
  const source: QueueCase[] = usingAssigned ? assigned : workSeed;

  const visible = source.filter((row) => {
    if (statusFilter !== "all" && row.status !== statusFilter) return false;
    const q = queryText.trim().toLowerCase();
    if (!q) return true;
    const extra = details[row.case_id];
    return (
      row.case_id.toLowerCase().includes(q) ||
      row.primary_entity_id.toLowerCase().includes(q) ||
      row.status.toLowerCase().includes(q) ||
      (extra?.assignee_id ?? "").toLowerCase().includes(q)
    );
  });

  return (
    <main id="main" className="page cases-page">
      <header className="page-head">
        <div>
          <p className="kicker">Investigator desk</p>
          <h1>My cases</h1>
        </div>
        {canQueue && (
          <button type="button" className="btn ghost" onClick={() => void navigate({ to: "/manager/queue" })}>
            Team queue
          </button>
        )}
      </header>

      {!runId && (
        <section className="empty">
          <h2>No active run</h2>
          <p>
            There is no detection run in this browser yet. A manager loads a batch from the queue
            page; the run id is then stored locally so investigators can open work.
          </p>
        </section>
      )}

      {runId && (
        <>
          {usingAssigned ? (
            <p className="banner ok">Showing cases assigned to {user.display_name}.</p>
          ) : (
            <p className="banner">
              No cases have `assignee_id` on this run (assignment is not exposed by the current
              API). Showing harm-priority and selected work from GET /runs/{"{id}"}/queue.
            </p>
          )}

          <div className="toolbar">
            <label className="grow">
              <span className="sr">Search</span>
              <input
                type="search"
                placeholder="Search case or provider…"
                value={queryText}
                onChange={(e) => setQueryText(e.target.value)}
              />
            </label>
            <label>
              Status
              <select value={statusFilter} onChange={(e) => setStatusFilter(e.target.value)}>
                <option value="all">All</option>
                {[...new Set(source.map((r) => r.status))].map((s) => (
                  <option key={s} value={s}>
                    {s}
                  </option>
                ))}
              </select>
            </label>
          </div>

          {(queueQuery.isLoading || detailsQuery.isLoading) && <p className="muted">Loading cases…</p>}
          {queueQuery.error && <p className="error-text">{(queueQuery.error as Error).message}</p>}
          {!queueQuery.isLoading && visible.length === 0 && (
            <p className="empty">No cases on the investigator worklist.</p>
          )}

          <ul className="case-list">
            {visible.map((row) => {
              const extra = details[row.case_id];
              return (
                <li key={row.case_id}>
                  <button
                    type="button"
                    className={`case-card lane-${row.lane} ${row.harm >= 4 ? "is-harm" : ""}`}
                    onClick={() =>
                      void navigate({
                        to: "/investigator/workspace/$caseId",
                        params: { caseId: row.case_id },
                      })
                    }
                  >
                    <header>
                      <span className="mono">{row.case_id}</span>
                      <LaneBadge lane={row.lane} />
                      <StatusBadge status={row.status} />
                    </header>
                    <p className="entity mono">{row.primary_entity_id}</p>
                    <dl>
                      <div>
                        <dt>Priority</dt>
                        <dd>
                          <HarmBadge harm={row.harm} />
                          <span className="mono"> P {pct(row.p_confirm)}</span>
                        </dd>
                      </div>
                      <div>
                        <dt>Flagged</dt>
                        <dd className="mono">{money(row.flagged_dollars)}</dd>
                      </div>
                      <div>
                        <dt>Hours</dt>
                        <dd className="mono">{hours(row.estimated_hours)}</dd>
                      </div>
                      <div>
                        <dt>Evidence</dt>
                        <dd>
                          <EvidenceBar value={row.evidence_strength} />
                        </dd>
                      </div>
                      <div>
                        <dt>Assignee</dt>
                        <dd className="mono">{extra?.assignee_id ?? "Unassigned"}</dd>
                      </div>
                    </dl>
                    <span className="open-hint">Open investigation workspace</span>
                  </button>
                </li>
              );
            })}
          </ul>
        </>
      )}
    </main>
  );
}
