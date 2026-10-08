import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { useNavigate } from "@tanstack/react-router";
import { useMemo, useState } from "react";
import { api, can } from "../../api/client";
import type { CaseDetail, QueueCase } from "../../api/types";
import { useAuth } from "../../auth/AuthProvider";
import { EvidenceBar } from "../../components/EvidenceBar";
import { HarmBadge, LaneBadge, StatusBadge } from "../../components/Badge";
import { hours, money, pct } from "../../lib/format";
import { readStoredRun } from "../../lib/runStore";

type Scope = "desk" | "mine" | "open";

export function InvestigatorCasesPage() {
  const { user } = useAuth();
  const navigate = useNavigate();
  const queryClient = useQueryClient();
  const [queryText, setQueryText] = useState("");
  const [statusFilter, setStatusFilter] = useState("all");
  const [scope, setScope] = useState<Scope>("desk");

  const stored = readStoredRun();
  const canCases = can(user, "case:read");
  const canQueue = can(user, "queue:read");
  const canReadBatches = can(user, "batch:read");
  const canAssign = can(user, "case:assign");

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
  const currentRunQuery = useQuery({
    queryKey: ["current-run"],
    queryFn: api.getCurrentRun,
    enabled: canQueue && !canReadBatches,
    retry: false,
  });
  const runId =
    batchQuery.data?.runs[0]?.run_id ?? currentRunQuery.data?.run_id ?? stored?.runId ?? null;

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

  const assignMut = useMutation({
    mutationFn: (caseId: string) => api.assignCase(caseId),
    onSuccess: () => {
      void queryClient.invalidateQueries({ queryKey: ["work-details"] });
      void queryClient.invalidateQueries({ queryKey: ["case"] });
      void queryClient.invalidateQueries({ queryKey: ["queue"] });
    },
  });

  if (!user) return null;
  if (!canCases) {
    return (
      <main id="main" className="page">
        <h1>Investigation worklist</h1>
        <p className="error-text">Your role cannot read cases.</p>
      </main>
    );
  }

  const details = detailsQuery.data ?? {};
  const mine = workSeed.filter((row) => details[row.case_id]?.assignee_id === user.id);
  const unassigned = workSeed.filter((row) => !details[row.case_id]?.assignee_id);

  const source: QueueCase[] =
    scope === "mine" ? mine : scope === "open" ? unassigned : workSeed;

  const visible = source.filter((row) => {
    if (statusFilter !== "all" && row.status !== statusFilter) return false;
    const q = queryText.trim().toLowerCase();
    if (!q) return true;
    const extra = details[row.case_id];
    const name = extra?.primary_entity?.name ?? "";
    return (
      row.case_id.toLowerCase().includes(q) ||
      row.primary_entity_id.toLowerCase().includes(q) ||
      row.status.toLowerCase().includes(q) ||
      name.toLowerCase().includes(q) ||
      (extra?.assignee_id ?? "").toLowerCase().includes(q)
    );
  });

  return (
    <main id="main" className="page cases-page">
      <header className="page-head">
        <div>
          <p className="kicker">Investigator desk</p>
          <h1>Worklist</h1>
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
            A manager loads a batch from the queue page. After that, this desk shows harm-priority
            and selected cases from the live run.
          </p>
        </section>
      )}

      {runId && (
        <>
          <p className="note">
            {mine.length > 0
              ? `${mine.length} case${mine.length === 1 ? "" : "s"} on your desk. Unassigned work stays in the team list until someone takes it.`
              : "Nothing is assigned to you yet. Open a case and take ownership, or claim it from this list."}
          </p>

          <div className="toolbar">
            <div className="scope-tabs" role="tablist" aria-label="Worklist scope">
              <button
                type="button"
                className={scope === "desk" ? "on" : ""}
                onClick={() => setScope("desk")}
              >
                Team desk <em>{workSeed.length}</em>
              </button>
              <button
                type="button"
                className={scope === "mine" ? "on" : ""}
                onClick={() => setScope("mine")}
              >
                Mine <em>{mine.length}</em>
              </button>
              <button
                type="button"
                className={scope === "open" ? "on" : ""}
                onClick={() => setScope("open")}
              >
                Unassigned <em>{unassigned.length}</em>
              </button>
            </div>
            <label className="grow">
              <span className="sr">Search</span>
              <input
                type="search"
                placeholder="Search case, provider, or specialty…"
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
            <p className="empty">No cases in this view.</p>
          )}

          <ul className="case-list">
            {visible.map((row) => {
              const extra = details[row.case_id];
              const name = extra?.primary_entity?.name ?? row.primary_entity_id;
              const specialty = extra?.primary_entity?.specialty;
              const mineRow = extra?.assignee_id === user.id;
              const ownerLabel = mineRow ? "You" : extra?.assignee_id ?? "Unassigned";
              return (
                <li key={row.case_id}>
                  <article className={`case-card lane-${row.lane}`}>
                    <button
                      type="button"
                      className="case-card-main"
                      onClick={() =>
                        void navigate({
                          to: "/investigator/workspace/$caseId",
                          params: { caseId: row.case_id },
                        })
                      }
                    >
                      <header>
                        <LaneBadge lane={row.lane} />
                        <StatusBadge status={row.status} />
                        <HarmBadge harm={row.harm} />
                        <span className="mono case-id">{row.case_id}</span>
                      </header>
                      <h2>{name}</h2>
                      <p className="entity-meta">
                        <span className="mono">{row.primary_entity_id}</span>
                        {specialty ? <span>{specialty}</span> : null}
                        <span>Owner {ownerLabel}</span>
                      </p>
                      {row.alert_group && (
                        <p className="muted" title={row.alert_group.text}>
                          {row.alert_group.n_alerts
                            ? `${row.alert_group.n_alerts} grouped alerts`
                            : extra?.grouping
                              ? `${extra.grouping.alert_count} grouped alerts`
                              : "Grouped alerts"}
                          {row.alert_group.n_entities > 1
                            ? ` · ${row.alert_group.n_entities} linked NPIs`
                            : ""}
                          {row.harm >= 4 ? " · urgent still visible" : ""}
                        </p>
                      )}
                      <dl>
                        <div>
                          <dt>Confirm chance</dt>
                          <dd>{pct(row.p_confirm)}</dd>
                        </div>
                        <div>
                          <dt>Flagged</dt>
                          <dd>{money(row.flagged_dollars)}</dd>
                        </div>
                        <div>
                          <dt>Hours</dt>
                          <dd>{hours(row.estimated_hours)}</dd>
                        </div>
                        <div>
                          <dt>Evidence</dt>
                          <dd>
                            <EvidenceBar value={row.evidence_strength} />
                          </dd>
                        </div>
                      </dl>
                    </button>
                    {canAssign && !mineRow && (
                      <button
                        type="button"
                        className="btn ghost take-btn"
                        disabled={assignMut.isPending}
                        onClick={() => assignMut.mutate(row.case_id)}
                      >
                        Take ownership
                      </button>
                    )}
                  </article>
                </li>
              );
            })}
          </ul>
        </>
      )}
    </main>
  );
}
