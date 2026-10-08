import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { useNavigate } from "@tanstack/react-router";
import { useEffect, useMemo, useState } from "react";
import { api, ApiError, can } from "../../api/client";
import type { Lane, QueueCase } from "../../api/types";
import { useAuth } from "../../auth/AuthProvider";
import { CaseDrawer } from "../../components/CaseDrawer";
import { EvidenceBar } from "../../components/EvidenceBar";
import { HarmBadge, LaneBadge, StatusBadge } from "../../components/Badge";
import { hours, horizonRisk, money, pct, screeningLabel, screeningTone, whyPriority } from "../../lib/format";
import { readStoredRun, writeStoredRun } from "../../lib/runStore";
import { QueueScene } from "../../three/QueueScene";
import "./queue.css";

type SortKey = "rank" | "ev" | "dollars" | "harm" | "hours" | "evidence" | "p";

const LANE_ORDER: Lane[] = ["harm_priority", "selected", "needs_evidence", "overflow"];

export function ManagerQueuePage() {
  const { user } = useAuth();
  const navigate = useNavigate();
  const queryClient = useQueryClient();
  const canQueue = can(user, "queue:read");
  const canLoad = can(user, "batch:load");
  const canStart = can(user, "run:start");
  const canReadBatches = can(user, "batch:read");

  const [queryText, setQueryText] = useState("");
  const [laneFilter, setLaneFilter] = useState<"all" | Lane>("all");
  const [statusFilter, setStatusFilter] = useState("all");
  const [sortKey, setSortKey] = useState<SortKey>("ev");
  const [openId, setOpenId] = useState<string | null>(null);
  const [compareIds, setCompareIds] = useState<string[]>([]);
  const [capacityDraft, setCapacityDraft] = useState(40);
  const [horizonDraft, setHorizonDraft] = useState(60);
  const [notice, setNotice] = useState<string | null>(null);

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
    batchQuery.data?.runs[0]?.run_id ?? stored?.runId ?? currentRunQuery.data?.run_id ?? null;

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

  const appliedCapacity = runQuery.data?.summary.capacity_hours ?? stored?.capacityHours ?? 40;
  const appliedHorizon = runQuery.data?.summary.horizon_days ?? stored?.horizonDays ?? 60;

  useEffect(() => {
    setCapacityDraft(appliedCapacity);
    setHorizonDraft(appliedHorizon);
  }, [appliedCapacity, appliedHorizon]);

  const hasExtract = Boolean(runId || batchId);
  const canRunDesk = hasExtract ? canStart : canLoad;

  const loadMut = useMutation({
    mutationFn: async (vars: { capacity: number; horizon: number }) => {
      if (hasExtract) {
        const run = await api.startRun({
          batch_id: batchId,
          horizon_days: vars.horizon,
          capacity_hours: vars.capacity,
        });
        return { kind: "run" as const, run };
      }
      const data = await api.loadBatch({
        adapter: "synthetic",
        profile: batchQuery.data?.profile ?? stored?.profile ?? "tiny",
        seed: batchQuery.data?.seed ?? stored?.seed ?? 7,
        horizon_days: vars.horizon,
        capacity_hours: vars.capacity,
        run_now: true,
      });
      return { kind: "batch" as const, data };
    },
    onSuccess: (payload) => {
      if (payload.kind === "run") {
        writeStoredRun({
          runId: payload.run.run_id,
          batchId: payload.run.batch_id,
          profile: batchQuery.data?.profile ?? stored?.profile ?? "tiny",
          seed: batchQuery.data?.seed ?? stored?.seed ?? 7,
          capacityHours: payload.run.capacity_hours ?? payload.run.summary.capacity_hours ?? capacityDraft,
          horizonDays: payload.run.horizon_days ?? payload.run.summary.horizon_days ?? horizonDraft,
        });
        setNotice("Queue re-laned on the existing extract. No new members were generated.");
      } else if (payload.data.run) {
        writeStoredRun({
          runId: payload.data.run.run_id,
          batchId: payload.data.batch_id,
          profile: payload.data.profile ?? "tiny",
          seed: payload.data.seed ?? 7,
          capacityHours: payload.data.run.capacity_hours ?? capacityDraft,
          horizonDays: payload.data.run.horizon_days ?? horizonDraft,
        });
        setNotice("Detection run completed. Queue reflects the new capacity and horizon.");
      }
      void queryClient.invalidateQueries({ queryKey: ["batches"] });
      void queryClient.invalidateQueries({ queryKey: ["run"] });
      void queryClient.invalidateQueries({ queryKey: ["queue"] });
      void queryClient.invalidateQueries({ queryKey: ["batch"] });
    },
  });

  function toggleCompare(caseId: string) {
    setCompareIds((prev) => {
      if (prev.includes(caseId)) return prev.filter((id) => id !== caseId);
      if (prev.length >= 2) return [prev[1], caseId];
      return [...prev, caseId];
    });
  }

  if (!user) return null;
  if (!canQueue) {
    return (
      <main id="main" className="page">
        <h1>Queue</h1>
        <p className="error-text">Your role cannot read the SIU queue.</p>
      </main>
    );
  }

  const rows = queueQuery.data ?? [];
  const nAlerts = runQuery.data?.n_alerts ?? runQuery.data?.summary.n_alerts ?? 0;
  const nCases = rows.length || runQuery.data?.n_cases || 0;
  const nSelected =
    rows.filter((r) => r.lane === "selected" || r.lane === "harm_priority").length ||
    runQuery.data?.summary.n_selected ||
    0;

  const filtered = useMemo(() => {
    const q = queryText.trim().toLowerCase();
    let list = rows.filter((row) => {
      if (laneFilter !== "all" && row.lane !== laneFilter) return false;
      if (statusFilter !== "all" && row.status !== statusFilter) return false;
      if (!q) return true;
      return (
        row.case_id.toLowerCase().includes(q) ||
        row.primary_entity_id.toLowerCase().includes(q) ||
        row.status.toLowerCase().includes(q) ||
        row.lane.toLowerCase().includes(q)
      );
    });
    const ranked = [...list];
    ranked.sort((a, b) => {
      if (sortKey === "ev") return (b.expected_value ?? 0) - (a.expected_value ?? 0);
      if (sortKey === "dollars") return b.flagged_dollars - a.flagged_dollars;
      if (sortKey === "harm") return b.harm - a.harm;
      if (sortKey === "hours") return b.estimated_hours - a.estimated_hours;
      if (sortKey === "evidence") return b.evidence_strength - a.evidence_strength;
      if (sortKey === "p") return b.p_confirm - a.p_confirm;
      const ia = LANE_ORDER.indexOf(a.lane);
      const ib = LANE_ORDER.indexOf(b.lane);
      if (ia !== ib) return ia - ib;
      return (b.expected_value ?? 0) - (a.expected_value ?? 0);
    });
    return ranked;
  }, [rows, queryText, laneFilter, statusFilter, sortKey]);

  const counts = {
    harm_priority: rows.filter((r) => r.lane === "harm_priority").length,
    selected: rows.filter((r) => r.lane === "selected").length,
    needs_evidence: rows.filter((r) => r.lane === "needs_evidence").length,
    overflow: rows.filter((r) => r.lane === "overflow").length,
  };

  const harmHours = sumHours(rows, "harm_priority");
  const selectedHours = sumHours(rows, "selected");
  const usedHours = harmHours + selectedHours;
  const unused = Math.max(0, appliedCapacity - usedHours);
  const monitorHours = sumHours(rows, "overflow");
  const evidenceHours = sumHours(rows, "needs_evidence");

  const currentErr = currentRunQuery.error as ApiError | undefined;
  const error =
    (batchesQuery.error as ApiError | undefined) ||
    (runQuery.error as ApiError | undefined) ||
    (queueQuery.error as ApiError | undefined) ||
    (loadMut.error as ApiError | undefined) ||
    (currentErr && currentErr.status !== 404 ? currentErr : undefined);

  const compared = rows.filter((row) => compareIds.includes(row.case_id));

  return (
    <main id="main" className="page queue-page">
      <header className="page-head">
        <div>
          <p className="kicker">Manager desk</p>
          <h1>SIU queue</h1>
        </div>
        <p className="funnel" aria-live="polite">
          <span className="stat-chip">
            <span>Alerts</span>
            <strong>{nAlerts}</strong>
          </span>
          <span className="stat-chip">
            <span>Cases</span>
            <strong>{nCases}</strong>
          </span>
          <span className="stat-chip">
            <span>Queued</span>
            <strong>{nSelected}</strong>
          </span>
        </p>
      </header>

      {!canRunDesk && (
        <p className="banner">
          Read-only. {hasExtract ? "Recompute requires `run:start`." : "First load requires `batch:load`."}
        </p>
      )}

      <section className="control-board" aria-label="Capacity and horizon">
        <div className="capacity-block">
          <label htmlFor="capacity">
            Team investigation capacity
            <strong className="mono">{capacityDraft.toFixed(0)} hours</strong>
          </label>
          <input
            id="capacity"
            type="range"
            min={8}
            max={80}
            step={1}
            value={capacityDraft}
            disabled={!canRunDesk || loadMut.isPending}
            onChange={(e) => setCapacityDraft(Number(e.target.value))}
          />
          <p className="muted">
            Applied run: <span className="mono">{hours(appliedCapacity)}</span>
            {usedHours > 0 && (
              <>
                {" "}
                · queued work <span className="mono">{hours(usedHours)}</span>
              </>
            )}
          </p>
        </div>
        <fieldset className="horizon">
          <legend>30 / 60 / 90 horizon</legend>
          {[30, 60, 90].map((h) => (
            <label key={h}>
              <input
                type="radio"
                name="horizon"
                value={h}
                checked={horizonDraft === h}
                disabled={!canRunDesk || loadMut.isPending}
                onChange={() => setHorizonDraft(h)}
              />
              {h}d
            </label>
          ))}
          <p className="muted">
            Applied: <span className="mono">{appliedHorizon}d</span>. Risk column uses F{appliedHorizon}.
          </p>
        </fieldset>
        {canRunDesk && (
          <button
            type="button"
            className="btn solid"
            disabled={loadMut.isPending}
            onClick={() => loadMut.mutate({ capacity: capacityDraft, horizon: horizonDraft })}
          >
            {loadMut.isPending
              ? hasExtract
                ? "Re-laning…"
                : "Running detection…"
              : hasExtract
                ? "Recompute queue"
                : "Load tiny run"}
          </button>
        )}
      </section>

      {loadMut.isPending && (
        <p className="banner" aria-live="polite">
          {hasExtract
            ? "Re-laning the existing extract via POST /api/v1/runs. Members are not regenerated."
            : "Generating extract, scoring rules/anomaly/graph, packing hours. This uses POST /api/v1/batches."}
        </p>
      )}
      {notice && <p className="banner ok">{notice}</p>}
      {error && <p className="error-text">{error.message}</p>}

      {!runId && !loadMut.isPending && (
        <section className="empty">
          <h2>No detection run</h2>
          <p>
            {canLoad
              ? "Load the tiny synthetic batch to fill this queue from the live API."
              : "A manager must load a batch first. Later recomputes use POST /api/v1/runs on that extract."}
          </p>
        </section>
      )}

      {runId && (
        <>
          <QueueScene
            hoursByLane={{
              harm_priority: harmHours,
              selected: selectedHours,
              needs_evidence: evidenceHours,
              overflow: monitorHours,
            }}
            selected={laneFilter}
            onSelect={(lane) => setLaneFilter(laneFilter === lane ? "all" : lane)}
          />
          <section className="lanes" aria-label="Queue lanes">
            <LaneStat
              lane="harm_priority"
              n={counts.harm_priority}
              active={laneFilter === "harm_priority"}
              onClick={() => setLaneFilter(laneFilter === "harm_priority" ? "all" : "harm_priority")}
            />
            <LaneStat
              lane="selected"
              n={counts.selected}
              active={laneFilter === "selected"}
              onClick={() => setLaneFilter(laneFilter === "selected" ? "all" : "selected")}
            />
            <LaneStat
              lane="needs_evidence"
              n={counts.needs_evidence}
              active={laneFilter === "needs_evidence"}
              onClick={() => setLaneFilter(laneFilter === "needs_evidence" ? "all" : "needs_evidence")}
            />
            <LaneStat
              lane="overflow"
              n={counts.overflow}
              active={laneFilter === "overflow"}
              onClick={() => setLaneFilter(laneFilter === "overflow" ? "all" : "overflow")}
            />
          </section>

          <section className="waterfall" aria-label="Capacity selection explanation">
            <h2>Why these cases were selected</h2>
            <ol>
              <li>
                Harm ≥ 4 is taken first
                <span className="mono">{hours(harmHours)}</span>
              </li>
              <li>
                Remaining hours packed by knapsack (selected lane)
                <span className="mono">{hours(selectedHours)}</span>
              </li>
              <li>
                Unused capacity
                <span className="mono">{hours(unused)}</span>
              </li>
              <li>
                Monitor (overflow) excluded — would exceed hours
                <span className="mono">{hours(monitorHours)}</span>
              </li>
              <li>
                Needs evidence — evidence strength below 0.40
                <span className="mono">{hours(evidenceHours)}</span>
              </li>
            </ol>
            <p className="muted">
              Harm ≥ 4 takes a reserved slice of hours. Remaining capacity is packed by expected
              value (recovery × dollars + harm term). The 45-day column is the CMS-style lead
              screening clock. Click a bar or lane chip to filter the table. Check two cases to compare.
            </p>
          </section>

          {compared.length > 0 && (
            <section className="compare-strip" aria-label="Side-by-side case compare">
              <header>
                <h2>Compare</h2>
                <button type="button" className="btn ghost" onClick={() => setCompareIds([])}>
                  Clear
                </button>
              </header>
              <div className={`compare-grid n-${compared.length}`}>
                {compared.map((row) => (
                  <article key={row.case_id}>
                    <p className="mono">{row.case_id}</p>
                    <p className="mono">{row.primary_entity_id}</p>
                    <LaneBadge lane={row.lane} />
                    <dl>
                      <div>
                        <dt>EV</dt>
                        <dd className="mono">{money(row.expected_value ?? 0)}</dd>
                      </div>
                      <div>
                        <dt>Harm</dt>
                        <dd className="mono">{row.harm}</dd>
                      </div>
                      <div>
                        <dt>Hours</dt>
                        <dd className="mono">{hours(row.estimated_hours)}</dd>
                      </div>
                      <div>
                        <dt>45-day</dt>
                        <dd className="mono">{screeningLabel(row.screening_days_left)}</dd>
                      </div>
                    </dl>
                    <p className="why">{whyPriority(row)}</p>
                  </article>
                ))}
              </div>
            </section>
          )}

          <div className="toolbar">
            <label className="grow">
              <span className="sr">Search cases</span>
              <input
                type="search"
                placeholder="Search case ID, provider, status…"
                value={queryText}
                onChange={(e) => setQueryText(e.target.value)}
              />
            </label>
            <label>
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
            <label>
              Sort
              <select value={sortKey} onChange={(e) => setSortKey(e.target.value as SortKey)}>
                <option value="rank">Lane rank</option>
                <option value="ev">Expected value</option>
                <option value="dollars">Flagged $</option>
                <option value="harm">Harm</option>
                <option value="p">P(confirm)</option>
                <option value="evidence">Evidence</option>
                <option value="hours">Hours</option>
              </select>
            </label>
          </div>

          {queueQuery.isLoading && <p className="muted">Loading queue…</p>}
          {!queueQuery.isLoading && filtered.length === 0 && (
            <p className="empty">No cases match the current filters.</p>
          )}

          <div className="table-wrap">
            <table className="grid">
              <thead>
                <tr>
                  <th>Compare</th>
                  <th>Case</th>
                  <th>Entity</th>
                  <th>Lane</th>
                  <th>Status</th>
                  <th>45-day</th>
                  <th>P(confirm)</th>
                  <th>Horizon risk</th>
                  <th>EV</th>
                  <th>Flagged</th>
                  <th>Members</th>
                  <th>Sev</th>
                  <th>Evidence</th>
                  <th>Hours</th>
                  <th>Why this rank</th>
                </tr>
              </thead>
              <tbody>
                {filtered.map((row) => (
                  <QueueRow
                    key={row.case_id}
                    row={row}
                    horizon={appliedHorizon}
                    selected={openId === row.case_id}
                    compared={compareIds.includes(row.case_id)}
                    onOpen={() => setOpenId(row.case_id)}
                    onCompare={() => toggleCompare(row.case_id)}
                  />
                ))}
              </tbody>
            </table>
          </div>
        </>
      )}

      {openId && (
        <CaseDrawer
          caseId={openId}
          onClose={() => setOpenId(null)}
          openHref={`/investigator/workspace/${openId}`}
        />
      )}

      {user.role === "investigator" && (
        <p className="muted foot">
          <button type="button" className="btn ghost" onClick={() => void navigate({ to: "/investigator/cases" })}>
            Open my cases
          </button>
        </p>
      )}
    </main>
  );
}

function sumHours(rows: QueueCase[], lane: Lane): number {
  return rows.filter((r) => r.lane === lane).reduce((acc, r) => acc + r.estimated_hours, 0);
}

function LaneStat({
  lane,
  n,
  active,
  onClick,
}: {
  lane: Lane;
  n: number;
  active: boolean;
  onClick: () => void;
}) {
  const labels: Record<Lane, string> = {
    harm_priority: "Harm priority",
    selected: "Selected",
    needs_evidence: "Needs evidence",
    overflow: "Monitor",
  };
  return (
    <button type="button" className={`lane-stat lane-${lane} ${active ? "on" : ""}`} onClick={onClick}>
      <span>{labels[lane]}</span>
      <strong className="mono">{n}</strong>
    </button>
  );
}

function QueueRow({
  row,
  horizon,
  selected,
  compared,
  onOpen,
  onCompare,
}: {
  row: QueueCase;
  horizon: number;
  selected: boolean;
  compared: boolean;
  onOpen: () => void;
  onCompare: () => void;
}) {
  const risk = horizonRisk(row, horizon);
  const sla = screeningTone(row.screening_days_left);
  return (
    <tr
      className={`lane-${row.lane} ${row.harm >= 4 ? "is-harm" : ""} ${selected ? "is-open" : ""}`}
      tabIndex={0}
      onClick={onOpen}
      onKeyDown={(e) => {
        if (e.key === "Enter" || e.key === " ") {
          e.preventDefault();
          onOpen();
        }
      }}
    >
      <td>
        <input
          type="checkbox"
          aria-label={`Compare ${row.case_id}`}
          checked={compared}
          onClick={(e) => e.stopPropagation()}
          onChange={onCompare}
        />
      </td>
      <td>
        <div className="case-cell">
          <strong className="mono">{row.case_id}</strong>
        </div>
      </td>
      <td className="mono">{row.primary_entity_id}</td>
      <td>
        <LaneBadge lane={row.lane} />
      </td>
      <td>
        <StatusBadge status={row.status} />
      </td>
      <td>
        <span className={`sla-chip sla-${sla}`}>{screeningLabel(row.screening_days_left)}</span>
      </td>
      <td className="mono">{pct(row.p_confirm)}</td>
      <td className="mono">{pct(risk)}</td>
      <td className="mono">{money(row.expected_value ?? 0)}</td>
      <td className="mono dollars">{money(row.flagged_dollars)}</td>
      <td className="mono">{row.members_affected}</td>
      <td>
        <HarmBadge harm={row.harm} />
        <span className="muted"> / {row.severity}</span>
      </td>
      <td>
        <EvidenceBar value={row.evidence_strength} />
      </td>
      <td className="mono">{hours(row.estimated_hours)}</td>
      <td className="why">{whyPriority(row)}</td>
    </tr>
  );
}
