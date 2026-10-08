import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { useCallback, useMemo, useState } from "react";
import { api, ApiError, can } from "../../api/client";
import type { Lane, QueueCase } from "../../api/types";
import { useAuth } from "../../auth/AuthProvider";
import { CaseDrawer } from "../../components/CaseDrawer";
import { LaneHoursChart } from "../../components/charts/LaneHoursChart";
import { PageHeader } from "../../components/ui/PageHeader";
import { Panel } from "../../components/ui/Panel";
import { EmptyState, ErrorState, LoadingState } from "../../components/ui/States";
import { StatTile } from "../../components/ui/StatTile";
import { hours, LANE_ORDER, laneLabel } from "../../lib/format";
import { readStoredRun, writeStoredRun } from "../../lib/runStore";
import { HistoryPanel } from "../cases/HistoryPanel";
import { AwsIngestPanel } from "./AwsIngestPanel";
import { CompareStrip } from "./CompareStrip";
import { DeskSettings, type DeskDraft } from "./DeskSettings";
import { FactorStripLegend } from "./FactorBars";
import { OverrideForm, type OverrideTarget } from "./OverrideForm";
import { QueueTable, type SortKey } from "./QueueTable";
import { DASH_LABEL } from "../../lib/scoreLabels";
import "./queue.css";

function sumHours(rows: QueueCase[], lane: Lane): number {
  return rows.filter((r) => r.lane === lane).reduce((acc, r) => acc + r.estimated_hours, 0);
}

function sortRows(rows: QueueCase[], key: SortKey): QueueCase[] {
  const laneIndex = (row: QueueCase) => LANE_ORDER.indexOf(row.lane);
  const by: Record<SortKey, (a: QueueCase, b: QueueCase) => number> = {
    rank: (a, b) => laneIndex(a) - laneIndex(b) || (b.rank_factors?.composite ?? 0) - (a.rank_factors?.composite ?? 0),
    p: (a, b) => b.p_confirm - a.p_confirm,
    severity: (a, b) => b.severity - a.severity,
    dollars: (a, b) => b.flagged_dollars - a.flagged_dollars,
    harm: (a, b) => b.harm - a.harm || b.members_affected - a.members_affected,
    hours: (a, b) => (a.screening_days_left ?? 99) - (b.screening_days_left ?? 99),
    evidence: (a, b) => b.evidence_strength - a.evidence_strength,
  };
  return [...rows].sort(by[key]);
}

export function ManagerQueuePage() {
  const { user } = useAuth();
  const queryClient = useQueryClient();
  const canQueue = can(user, "queue:read");
  const canLoad = can(user, "batch:load");
  const canStart = can(user, "run:start");
  const canReadBatches = can(user, "batch:read");
  const canOverride = can(user, "queue:configure") || can(user, "case:decide");

  const [queryText, setQueryText] = useState("");
  const [laneFilter, setLaneFilter] = useState<"all" | Lane>("all");
  const [statusFilter, setStatusFilter] = useState("all");
  const [sortKey, setSortKey] = useState<SortKey>("rank");
  const [openId, setOpenId] = useState<string | null>(null);
  const [compareIds, setCompareIds] = useState<string[]>([]);
  // Unsaved slider edits on top of the run's applied settings; cleared after a recompute.
  const [edits, setEdits] = useState<Partial<DeskDraft>>({});
  const [overrideTarget, setOverrideTarget] = useState<OverrideTarget | null>(null);
  const [notice, setNotice] = useState<string | null>(null);
  const [activeRunId, setActiveRunId] = useState<string | null>(null);

  const stored = readStoredRun();

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
    queryKey: ["run", "current"],
    queryFn: api.getCurrentRun,
    enabled: canQueue,
    retry: false,
  });
  const runId =
    activeRunId ?? currentRunQuery.data?.run_id ?? batchQuery.data?.runs[0]?.run_id ?? stored?.runId ?? null;
  const runQuery = useQuery({
    queryKey: ["run", runId],
    queryFn: () => api.getRun(runId!),
    enabled: Boolean(runId) && canQueue,
  });
  const queueQuery = useQuery({
    queryKey: ["queue", runId],
    queryFn: () => api.getQueue(runId!),
    enabled: Boolean(runId) && canQueue,
  });

  const applied: DeskDraft = {
    capacity: runQuery.data?.summary.capacity_hours ?? stored?.capacityHours ?? 40,
    horizon: runQuery.data?.summary.horizon_days ?? stored?.horizonDays ?? 60,
    slots: runQuery.data?.summary.max_slots ?? runQuery.data?.max_slots ?? 20,
    member: runQuery.data?.summary.member_weight ?? runQuery.data?.member_weight ?? 1,
  };
  const rankingPolicy = runQuery.data?.summary.ranking_policy ?? runQuery.data?.ranking_policy;

  const draft: DeskDraft = { ...applied, ...edits };

  const hasExtract = Boolean(runId || batchId);
  const canRunDesk = hasExtract ? canStart : canLoad;

  const loadMut = useMutation({
    mutationFn: async (vars: DeskDraft) => {
      if (hasExtract) {
        const run = await api.startRun({
          batch_id: batchId,
          horizon_days: vars.horizon,
          capacity_hours: vars.capacity,
          max_slots: vars.slots,
          member_weight: vars.member,
        });
        return { kind: "run" as const, run };
      }
      const data = await api.loadBatch({
        adapter: "synthetic",
        profile: batchQuery.data?.profile ?? stored?.profile ?? "tiny",
        seed: batchQuery.data?.seed ?? stored?.seed ?? 7,
        horizon_days: vars.horizon,
        capacity_hours: vars.capacity,
        max_slots: vars.slots,
        member_weight: vars.member,
        run_now: true,
      });
      return { kind: "batch" as const, data };
    },
    onSuccess: (payload, vars) => {
      setEdits({});
      if (payload.kind === "run") {
        setActiveRunId(payload.run.run_id);
        queryClient.setQueryData(["run", payload.run.run_id], payload.run);
        writeStoredRun({
          runId: payload.run.run_id,
          batchId: payload.run.batch_id,
          profile: batchQuery.data?.profile ?? stored?.profile ?? "tiny",
          seed: batchQuery.data?.seed ?? stored?.seed ?? 7,
          capacityHours: payload.run.capacity_hours ?? payload.run.summary.capacity_hours ?? vars.capacity,
          horizonDays: payload.run.horizon_days ?? payload.run.summary.horizon_days ?? vars.horizon,
        });
        setNotice(
          `Queue re-laned on a ${vars.horizon}-day window with ${vars.capacity.toFixed(0)} h, ${vars.slots} slots, people weight ${vars.member.toFixed(1)}×.`,
        );
      } else if (payload.data.run) {
        setActiveRunId(payload.data.run.run_id);
        writeStoredRun({
          runId: payload.data.run.run_id,
          batchId: payload.data.batch_id,
          profile: payload.data.profile ?? "tiny",
          seed: payload.data.seed ?? 7,
          capacityHours: payload.data.run.capacity_hours ?? vars.capacity,
          horizonDays: payload.data.run.horizon_days ?? vars.horizon,
        });
        setNotice("Detection run completed. Queue reflects the new capacity and horizon.");
      }
      void queryClient.invalidateQueries({ queryKey: ["batches"] });
      void queryClient.invalidateQueries({ queryKey: ["run"] });
      void queryClient.invalidateQueries({ queryKey: ["queue"] });
      void queryClient.invalidateQueries({ queryKey: ["batch"] });
      void queryClient.invalidateQueries({ queryKey: ["case-history"] });
    },
  });

  const overrideMut = useMutation({
    mutationFn: (vars: OverrideTarget & { reason: string }) =>
      api.overrideRank(vars.caseId, { action: vars.action, reason: vars.reason }),
    onSuccess: (data) => {
      setNotice(data.note);
      setOverrideTarget(null);
      void queryClient.invalidateQueries({ queryKey: ["queue"] });
      void queryClient.invalidateQueries({ queryKey: ["case"] });
    },
  });

  const closeDrawer = useCallback(() => setOpenId(null), []);
  const rows = useMemo(() => queueQuery.data ?? [], [queueQuery.data]);
  const filtered = useMemo(() => {
    const q = queryText.trim().toLowerCase();
    const list = rows.filter((row) => {
      if (laneFilter !== "all" && row.lane !== laneFilter) return false;
      if (statusFilter !== "all" && row.status !== statusFilter) return false;
      if (!q) return true;
      return [row.case_id, row.primary_entity_id, row.status, row.lane].some((v) => v.toLowerCase().includes(q));
    });
    return sortRows(list, sortKey);
  }, [rows, queryText, laneFilter, statusFilter, sortKey]);

  if (!user) return null;
  if (!canQueue) {
    return (
      <main id="main" className="page">
        <PageHeader eyebrow="Manager desk" title="SIU queue" />
        <ErrorState title="Access denied" error="Your role cannot read the SIU queue." />
      </main>
    );
  }

  const hoursByLane = Object.fromEntries(LANE_ORDER.map((lane) => [lane, sumHours(rows, lane)])) as Record<Lane, number>;
  const casesByLane = Object.fromEntries(
    LANE_ORDER.map((lane) => [lane, rows.filter((r) => r.lane === lane).length]),
  ) as Record<Lane, number>;
  const capacityPack = runQuery.data?.summary.capacity ?? runQuery.data?.capacity;
  const capacityHours = capacityPack?.capacity_hours ?? applied.capacity;
  const overrideHours = capacityPack?.priority_override_hours ?? hoursByLane.harm_priority;
  const selectedHours = capacityPack?.selected_hours ?? hoursByLane.selected;
  const deskHours = capacityPack?.capacity_used_hours ?? overrideHours + selectedHours;
  const overCapacity = capacityPack?.over_capacity_hours ?? Math.max(0, deskHours - capacityHours);
  const overrideWarn = capacityPack?.override_share_warning ?? false;
  const nAlerts = runQuery.data?.n_alerts ?? runQuery.data?.summary.n_alerts ?? 0;
  const nCases = rows.length || runQuery.data?.n_cases || 0;
  const nToday = casesByLane.harm_priority + casesByLane.selected || runQuery.data?.summary.n_selected || 0;

  const currentErr = currentRunQuery.error as ApiError | undefined;
  const error =
    batchesQuery.error ||
    runQuery.error ||
    queueQuery.error ||
    loadMut.error ||
    overrideMut.error ||
    (currentErr && currentErr.status !== 404 ? currentErr : null);
  const compared = rows.filter((row) => compareIds.includes(row.case_id));
  const toggleLane = (lane: Lane) => setLaneFilter((prev) => (prev === lane ? "all" : lane));

  return (
    <main id="main" className="page queue-page">
      <PageHeader
        eyebrow="Manager desk"
        title="SIU queue"
        description="Cases ranked by combined factors inside investigator capacity. Harm goes first; humans decide what is worked."
      />

      {!canRunDesk ? (
        <p className="banner info">
          Read-only. {hasExtract ? "Recomputing requires the run:start permission." : "The first load requires batch:load."}
        </p>
      ) : null}
      {loadMut.isPending ? (
        <p className="banner info" aria-live="polite">
          {hasExtract
            ? "Re-laning the existing extract. Members are not regenerated."
            : "Generating the extract, scoring rules, anomalies and graph, then packing hours…"}
        </p>
      ) : null}
      {notice ? (
        <p className="banner ok" role="status">
          {notice}
        </p>
      ) : null}
      {error ? <ErrorState title="The queue could not be updated" error={error} /> : null}

      {runId ? (
        <dl className="stat-grid kpis">
          <StatTile label="Flags" value={nAlerts} hint="Raw detector hits" />
          <StatTile label="Cases" value={nCases} hint="After grouping" />
          <StatTile
            label="Desk"
            value={nToday}
            hint={`${hours(deskHours)} used · ${hours(capacityHours)} capacity`}
          />
          <StatTile label="Harm" value={casesByLane.harm_priority} tone="harm" />
          <StatTile label="Wait" value={casesByLane.overflow} hint="Still open, not dismissed" />
        </dl>
      ) : null}

      <div className="queue-top">
        {runId ? (
          <Panel id="capacity" eyebrow="Capacity" title="Hours by lane">
            {overCapacity > 0 ? (
              <p className="banner warn">
                Today&apos;s desk uses {hours(deskHours)} against {hours(capacityHours)} of capacity, {hours(overCapacity)}{" "}
                over. Priority-override hours ({hours(overrideHours)}) count against capacity.
              </p>
            ) : (
              <p className="muted">
                Priority-override hours {hours(overrideHours)} plus selected {hours(selectedHours)} use {hours(deskHours)} of{" "}
                {hours(capacityHours)} capacity.
              </p>
            )}
            {overrideWarn ? (
              <p className="banner warn">
                Priority-override hours are more than 35% of capacity. The desk is spending most of its budget on harm
                overrides.
              </p>
            ) : null}
            {queueQuery.isLoading ? (
              <LoadingState label="Loading lanes…" />
            ) : (
              <LaneHoursChart
                hoursByLane={hoursByLane}
                casesByLane={casesByLane}
                capacityHours={capacityHours}
                selected={laneFilter}
                onSelect={toggleLane}
              />
            )}
          </Panel>
        ) : null}
        <DeskSettings
          draft={draft}
          applied={applied}
          deskHours={deskHours}
          disabled={!canRunDesk || loadMut.isPending}
          canRun={canRunDesk}
          hasExtract={hasExtract}
          pending={loadMut.isPending}
          onChange={(next) => setEdits(next)}
          onRun={(next) => {
            if (!loadMut.isPending) loadMut.mutate(next);
          }}
        />
      </div>

      {!runId && !loadMut.isPending ? (
        <EmptyState title="No detection run yet">
          {canLoad
            ? "Load the tiny synthetic batch to fill this queue from the live API."
            : "A manager must load a batch first. Later recomputes re-lane that extract."}
        </EmptyState>
      ) : null}

      {overrideTarget ? (
        <OverrideForm
          target={overrideTarget}
          pending={overrideMut.isPending}
          onCancel={() => setOverrideTarget(null)}
          onSubmit={(reason) => overrideMut.mutate({ ...overrideTarget, reason })}
        />
      ) : null}

      {compared.length > 0 ? (
        <CompareStrip rows={compared} policy={rankingPolicy} onClear={() => setCompareIds([])} />
      ) : null}

      {runId ? (
        <Panel
          id="queue"
          eyebrow="Queue"
          title="Ranked cases"
          description="Select a case to open its file. Tick two cases to compare why they rank."
          actions={<span className="badge">{filtered.length} shown</span>}
        >
          <div className="toolbar">
            <div className="segmented" role="group" aria-label="Filter by lane">
              <button type="button" aria-pressed={laneFilter === "all"} onClick={() => setLaneFilter("all")}>
                All <span className="count">{rows.length}</span>
              </button>
              {LANE_ORDER.map((lane) => (
                <button key={lane} type="button" aria-pressed={laneFilter === lane} onClick={() => toggleLane(lane)}>
                  {laneLabel(lane)} <span className="count">{casesByLane[lane]}</span>
                </button>
              ))}
            </div>
            <label className="field grow">
              Search
              <input
                type="search"
                placeholder="Case ID, provider, status…"
                value={queryText}
                onChange={(e) => setQueryText(e.target.value)}
              />
            </label>
            <label className="field">
              Status
              <select value={statusFilter} onChange={(e) => setStatusFilter(e.target.value)}>
                <option value="all">All</option>
                {[...new Set(rows.map((r) => r.status))].map((s) => (
                  <option key={s} value={s}>
                    {s}
                  </option>
                ))}
              </select>
            </label>
            <label className="field">
              Sort
              <select value={sortKey} onChange={(e) => setSortKey(e.target.value as SortKey)}>
                <option value="rank">Lane, then rank</option>
                <option value="p">{DASH_LABEL.chance}</option>
                <option value="severity">{DASH_LABEL.severity}</option>
                <option value="dollars">{DASH_LABEL.paid}</option>
                <option value="harm">{DASH_LABEL.harm}</option>
                <option value="evidence">{DASH_LABEL.proof}</option>
                <option value="hours">{DASH_LABEL.time}</option>
              </select>
            </label>
          </div>
          <FactorStripLegend />
          {queueQuery.isLoading ? <LoadingState label="Loading queue…" /> : null}
          {!queueQuery.isLoading && filtered.length === 0 ? (
            <EmptyState title="No cases match" compact>
              Change the lane, status or search filters.
            </EmptyState>
          ) : null}
          {filtered.length > 0 ? (
            <QueueTable
              rows={filtered}
              openId={openId}
              compareIds={compareIds}
              canOverride={canOverride}
              onOpen={setOpenId}
              onCompare={(caseId) =>
                setCompareIds((prev) =>
                  prev.includes(caseId) ? prev.filter((id) => id !== caseId) : [...prev.slice(-1), caseId],
                )
              }
              onOverride={setOverrideTarget}
            />
          ) : null}
          <details className="policy">
            <summary>How today&apos;s queue is recommended</summary>
            <p>
              {rankingPolicy?.note ??
                "The ranking proposes a top-N desk from combined factors and investigator capacity. Investigators decide. Cases outside today's slots stay open."}
            </p>
            <ol className="compact-list">
              <li>Harm ≥ 4 is taken first for member safety ({hours(hoursByLane.harm_priority)}).</li>
              <li>Remaining hours are packed on the combined rank ({hours(hoursByLane.selected)}).</li>
              <li>
                {overCapacity > 0
                  ? `Over capacity: the desk fills ${hours(deskHours)}, ${hours(overCapacity)} more than the ${hours(applied.capacity)} set.`
                  : `Unused capacity: ${hours(applied.capacity - deskHours)}.`}
              </li>
              <li>
                Tracked backlog, outside hours or the {applied.slots}-slot cap, still open ({hours(hoursByLane.overflow)}).
              </li>
              <li>Gather evidence: strength below 0.40 ({hours(hoursByLane.needs_evidence)}).</li>
            </ol>
          </details>
        </Panel>
      ) : null}

      {canQueue ? <AwsIngestPanel /> : null}

      {canQueue ? (
        <HistoryPanel
          title="Case history"
          description="Decided SIU cases, earlier runs after a recompute, and prior investigations from the extract. Ten rows per page."
        />
      ) : null}

      {openId ? <CaseDrawer caseId={openId} onClose={closeDrawer} /> : null}
    </main>
  );
}
