import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { Link } from "@tanstack/react-router";
import { useMemo, useState } from "react";
import { api, can } from "../../api/client";
import type { CaseDetail, QueueCase } from "../../api/types";
import { useAuth } from "../../auth/AuthProvider";
import { PageHeader } from "../../components/ui/PageHeader";
import { Panel } from "../../components/ui/Panel";
import { EmptyState, ErrorState, LoadingState } from "../../components/ui/States";
import { StatTile } from "../../components/ui/StatTile";
import { count, hours } from "../../lib/format";
import { readStoredRun } from "../../lib/runStore";
import { WorklistTable } from "./WorklistTable";
import "./cases.css";

type Scope = "desk" | "mine" | "open";

const SCOPE_LABELS: Record<Scope, string> = { desk: "Team desk", mine: "Mine", open: "Unassigned" };

export function InvestigatorCasesPage() {
  const { user } = useAuth();
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
        <PageHeader eyebrow="Investigator desk" title="Worklist" />
        <ErrorState title="Access denied" error="Your role cannot read cases." />
      </main>
    );
  }

  const details = detailsQuery.data ?? {};
  const mine = workSeed.filter((row) => details[row.case_id]?.assignee_id === user.id);
  const unassigned = workSeed.filter((row) => !details[row.case_id]?.assignee_id);
  const byScope: Record<Scope, QueueCase[]> = { desk: workSeed, mine, open: unassigned };
  const source = byScope[scope];

  const q = queryText.trim().toLowerCase();
  const visible = source.filter((row) => {
    if (statusFilter !== "all" && row.status !== statusFilter) return false;
    if (!q) return true;
    const extra = details[row.case_id];
    return [
      row.case_id,
      row.primary_entity_id,
      row.status,
      extra?.primary_entity?.name ?? "",
      extra?.primary_entity?.specialty ?? "",
      extra?.assignee_id ?? "",
    ].some((value) => value.toLowerCase().includes(q));
  });
  const harmCount = workSeed.filter((row) => row.harm >= 4).length;
  const deskHours = workSeed.reduce((acc, row) => acc + row.estimated_hours, 0);
  const error = queueQuery.error ?? detailsQuery.error ?? assignMut.error;

  return (
    <main id="main" className="page cases-page">
      <PageHeader
        eyebrow="Investigator desk"
        title="Worklist"
        description="Harm-priority and selected cases from the live run. Open a case to review evidence, network, claims and the brief."
        actions={
          canQueue ? (
            <Link to="/manager/queue" className="btn ghost">
              Team queue
            </Link>
          ) : null
        }
      />

      {!runId ? (
        <EmptyState title="No active run">
          A manager loads a batch from the queue page. After that, this desk shows harm-priority and selected cases
          from the live run.
        </EmptyState>
      ) : (
        <>
          <dl className="stat-grid">
            <StatTile label="On the team desk" value={workSeed.length} hint={`${hours(deskHours)} estimated`} />
            <StatTile label="Assigned to you" value={mine.length} />
            <StatTile label="Unassigned" value={unassigned.length} />
            <StatTile label="Harm priority" value={harmCount} tone="harm" />
          </dl>

          {error ? <ErrorState title="Cases could not be loaded" error={error} /> : null}

          <Panel
            id="worklist"
            eyebrow="Cases"
            title={SCOPE_LABELS[scope]}
            description={
              mine.length > 0
                ? `${count(mine.length, "case")} assigned to you. Unassigned work stays in the team list until someone takes it.`
                : "Nothing is assigned to you yet. Open a case and take ownership, or claim it from this list."
            }
            actions={<span className="badge">{visible.length} shown</span>}
          >
            <div className="toolbar">
              <div className="segmented" role="group" aria-label="Worklist scope">
                {(Object.keys(SCOPE_LABELS) as Scope[]).map((key) => (
                  <button key={key} type="button" aria-pressed={scope === key} onClick={() => setScope(key)}>
                    {SCOPE_LABELS[key]} <span className="count">{byScope[key].length}</span>
                  </button>
                ))}
              </div>
              <label className="field grow">
                Search
                <input
                  type="search"
                  placeholder="Case, provider, specialty or owner…"
                  value={queryText}
                  onChange={(e) => setQueryText(e.target.value)}
                />
              </label>
              <label className="field">
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
            {queueQuery.isLoading || detailsQuery.isLoading ? <LoadingState label="Loading cases…" /> : null}
            {!queueQuery.isLoading && visible.length === 0 ? (
              <EmptyState title="No cases in this view" compact>
                Try another scope or clear the search.
              </EmptyState>
            ) : null}
            {visible.length > 0 ? (
              <WorklistTable
                rows={visible}
                details={details}
                userId={user.id}
                canAssign={canAssign}
                assigning={assignMut.isPending ? assignMut.variables : undefined}
                onAssign={(caseId) => assignMut.mutate(caseId)}
              />
            ) : null}
          </Panel>
        </>
      )}
    </main>
  );
}
