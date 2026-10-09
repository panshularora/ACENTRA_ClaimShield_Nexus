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
import { hours, LANE_ORDER, laneLabel } from "../../lib/format";
import { rankedToday } from "../../lib/queueSlots";
import { readStoredRun, writeStoredRun } from "../../lib/runStore";
import { HistoryPanel } from "../cases/HistoryPanel";
import { AwsIngestPanel } from "./AwsIngestPanel";
import { CompareStrip } from "./CompareStrip";
import { DeskSettings, type DeskDraft } from "./DeskSettings";
import { OverrideForm, type OverrideTarget } from "./OverrideForm";
import { KpiCard, LaneMixCard, SlotFillCard } from "./DashWidgets";
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
  const todayRows = useMemo(() => rankedToday(rows, draft.slots), [rows, draft.slots]);
  const todayIds = useMemo(() => new Set(todayRows.map((row) => row.case_id)), [todayRows]);
  const filtered = useMemo(() => {
    const q = queryText.trim().toLowerCase();
    const source =
      laneFilter === "all"
        ? todayRows
        : rows.filter((row) => {
            if (row.lane !== laneFilter) return false;
            if (laneFilter === "harm_priority" || laneFilter === "selected") return todayIds.has(row.case_id);
            return true;
          });
    const list = source.filter((row) => {
      if (statusFilter !== "all" && row.status !== statusFilter) return false;
      if (!q) return true;
      return [row.case_id, row.primary_entity_id, row.status, row.lane].some((v) => v.toLowerCase().includes(q));
    });
    return sortRows(list, sortKey);
  }, [rows, todayRows, todayIds, queryText, laneFilter, statusFilter, sortKey]);

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
  const nCases = todayRows.length;

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
        description="Harm goes first. Rank packs the rest into investigator hours. A person still decides."
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
        <section className="dash-top" aria-label="Desk snapshot">
          <KpiCard
            label="Patterns"
            hint="Hits grouped into cases"
            value={nAlerts}
            tone="blue"
            spark={rows.slice(0, 12).map((r) => r.alert_group?.n_alerts ?? 1)}
          />
          <KpiCard
            label="Cases"
            hint={`${draft.slots} slots today`}
            value={nCases}
            tone="amber"
            spark={todayRows.slice(0, 12).map((r) => r.rank_factors?.composite ?? 0)}
          />
          <KpiCard
            label="Hours packed"
            hint={`of ${hours(capacityHours)} capacity`}
            value={hours(deskHours)}
            tone="orange"
            spark={todayRows.slice(0, 12).map((r) => r.estimated_hours)}
          />
          <KpiCard
            label="Harm first"
            hint="Member-safety first"
            value={todayRows.filter((r) => r.lane === "harm_priority").length}
            tone="plum"
            spark={todayRows.slice(0, 12).map((r) => r.harm)}
          />
          <LaneMixCard casesByLane={casesByLane} selected={laneFilter} onSelect={toggleLane} />
          <SlotFillCard filled={todayRows.length} slots={draft.slots} />
        </section>
      ) : null}
      {overCapacity > 0 ? (
        <p className="banner warn">
          Today&apos;s desk uses {hours(deskHours)} against {hours(capacityHours)} of capacity, {hours(overCapacity)}{" "}
          over.
        </p>
      ) : null}
      {overrideWarn ? (
        <p className="banner warn">
          Harm-priority hours are more than 35% of capacity.
        </p>
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
      >
        {runId ? (
          queueQuery.isLoading ? (
            <LoadingState label="Loading lanes…" />
          ) : (
            <LaneHoursChart
              hoursByLane={hoursByLane}
              casesByLane={casesByLane}
              capacityHours={capacityHours}
              selected={laneFilter}
              onSelect={toggleLane}
            />
          )
        ) : null}
      </DeskSettings>

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
          className="dash-panel"
          eyebrow="Queue"
          title="Ranked cases"
          description="Open a case for the packet. Tick two cases to compare rank."
          actions={<span className="badge">{filtered.length} of {draft.slots} slots</span>}
        >
          <div className="toolbar">
            <div className="segmented" role="group" aria-label="Filter by priority">
              <button type="button" aria-pressed={laneFilter === "all"} onClick={() => setLaneFilter("all")}>
                Today <span className="count">{todayRows.length}</span>
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

      {canQueue ? (
        <details className="desk-more">
          <summary>AWS ingest and case history</summary>
          <AwsIngestPanel />
          <HistoryPanel
            title="Case history"
            description="Ten rows per page. Outcomes are substantiated, education, referred, or unsubstantiated."
          />
        </details>
      ) : null}

      {openId ? <CaseDrawer caseId={openId} onClose={closeDrawer} /> : null}
    </main>
  );
}
