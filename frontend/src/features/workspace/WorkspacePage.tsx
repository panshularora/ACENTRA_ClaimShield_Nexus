import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { Link, useParams } from "@tanstack/react-router";
import { useCallback, useState } from "react";
import { api, ApiError, can } from "../../api/client";
import type { Cite } from "../../api/types";
import { useAuth } from "../../auth/AuthProvider";
import { EvidenceBar } from "../../components/EvidenceBar";
import { HarmBadge, LaneBadge, StatusBadge } from "../../components/Badge";
import { hours, money, pct, screeningLabel, screeningTone } from "../../lib/format";
import { FactorBars } from "../queue/FactorBars";
import { BriefPanel } from "./BriefPanel";
import { ClaimsTable } from "./ClaimsTable";
import { DecisionBar } from "./DecisionBar";
import { EvidenceDrawer } from "./EvidenceDrawer";
import { FindingsPanel } from "./FindingsPanel";
import { NetworkPanel } from "./NetworkPanel";
import { TimelinePanel } from "./TimelinePanel";
import "./workspace-siu.css";

const TABS = ["overview", "findings", "brief", "claims", "timeline", "network", "decide"] as const;
type WorkspaceTab = (typeof TABS)[number];

function parseTab(raw: string | null | undefined): WorkspaceTab {
  const value = (raw ?? "").replace("#", "");
  return (TABS as readonly string[]).includes(value) ? (value as WorkspaceTab) : "overview";
}

export function WorkspacePage() {
  const { caseId } = useParams({ from: "/investigator/workspace/$caseId" });
  const { user } = useAuth();
  const queryClient = useQueryClient();
  const [unmask, setUnmask] = useState(false);
  const [itemId, setItemId] = useState<string | null>(null);
  const [tab, setTab] = useState<WorkspaceTab>(() =>
    typeof window === "undefined" ? "overview" : parseTab(window.location.hash),
  );

  const go = useCallback((next: WorkspaceTab) => {
    setTab(next);
    if (typeof window !== "undefined") {
      window.history.replaceState(null, "", `#${next}`);
    }
  }, []);

  const canRead = can(user, "case:read");
  const canDecide = can(user, "case:decide");
  const canAssign = can(user, "case:assign");

  const caseQuery = useQuery({
    queryKey: ["case", caseId],
    queryFn: () => api.getCase(caseId),
    enabled: canRead,
  });
  const briefQuery = useQuery({
    queryKey: ["brief", caseId],
    queryFn: () => api.getBrief(caseId),
    enabled: canRead,
  });
  const claimsQuery = useQuery({
    queryKey: ["claims", caseId, unmask],
    queryFn: () => api.getClaims(caseId, unmask),
    enabled: canRead,
  });
  const timelineQuery = useQuery({
    queryKey: ["timeline", caseId, unmask],
    queryFn: () => api.getTimeline(caseId, unmask),
    enabled: canRead,
  });
  const networkQuery = useQuery({
    queryKey: ["network", caseId, unmask],
    queryFn: () => api.getNetwork(caseId, 2, unmask),
    enabled: canRead,
  });

  const assignMut = useMutation({
    mutationFn: () => api.assignCase(caseId),
    onSuccess: () => {
      void queryClient.invalidateQueries({ queryKey: ["case", caseId] });
      void queryClient.invalidateQueries({ queryKey: ["queue"] });
    },
  });

  const decideMut = useMutation({
    mutationFn: (vars: {
      action: "escalate" | "monitor" | "dismiss" | "needs_evidence";
      reason: string;
      ladder_step?: string | null;
      evidence_refs?: string[];
    }) => api.decide(caseId, vars),
    onSuccess: () => {
      void queryClient.invalidateQueries({ queryKey: ["case", caseId] });
      void queryClient.invalidateQueries({ queryKey: ["brief", caseId] });
      void queryClient.invalidateQueries({ queryKey: ["queue"] });
      void queryClient.invalidateQueries({ queryKey: ["wiki-proposals"] });
    },
  });

  const openCite = useCallback((cite: Cite) => setItemId(cite.id), []);
  const openRef = useCallback((ref: string) => {
    if (ref.startsWith("line:") || ref.startsWith("alert:") || ref.startsWith("claim:") || ref.startsWith("provider:")) {
      setItemId(ref);
    }
  }, []);
  const openLine = useCallback((lineId: string) => setItemId(`line:${lineId}`), []);
  const onNode = useCallback((id: string, type: string) => {
    if (type === "provider") setItemId(`provider:${id}`);
  }, []);

  if (!user) return null;
  if (!canRead) {
    return (
      <main id="main" className="page">
        <h1>Investigation workspace</h1>
        <p className="error-text">Your role cannot read cases.</p>
      </main>
    );
  }

  const data = caseQuery.data;
  const err = (q: { error: unknown }) => (q.error ? (q.error as Error).message : null);
  const closed = Boolean(data && data.status !== "open");
  const findingCount = data
    ? new Set(data.alerts.map((alert) => alert.rule_id ?? alert.alert_id)).size
    : 0;
  const claimCount = claimsQuery.data?.rows.length ?? 0;
  const menu = [
    { id: "overview" as const, label: "Overview" },
    { id: "findings" as const, label: "Findings", count: findingCount },
    { id: "brief" as const, label: "Brief" },
    { id: "claims" as const, label: "Claims", count: claimCount },
    { id: "timeline" as const, label: "Timeline" },
    { id: "network" as const, label: "Network" },
    { id: "decide" as const, label: "Decide" },
  ];

  return (
    <main id="main" className="workspace workspace-shell">
      <header className="ws-head">
        <div className="ws-head-id">
          <p className="kicker">Investigation · suspicion only</p>
          <h1 id="sum-title">{data?.primary_entity?.name ?? caseId}</h1>
          <p className="entity-line">
            <span className="mono muted">{caseId}</span>
            {data?.primary_entity_id && <span className="mono">{data.primary_entity_id}</span>}
            {data?.primary_entity?.specialty && (
              <span className="muted">{data.primary_entity.specialty}</span>
            )}
            {data?.primary_entity?.kind && <span className="muted">{data.primary_entity.kind}</span>}
          </p>
        </div>
        <div className="ws-head-actions">
          <Link to="/investigator/cases" className="btn ghost">
            Worklist
          </Link>
          {data && canAssign && data.assignee_id !== user.id && (
            <button
              type="button"
              className="btn ghost"
              disabled={assignMut.isPending}
              onClick={() => assignMut.mutate()}
            >
              {assignMut.isPending ? "Taking…" : "Take ownership"}
            </button>
          )}
          <button type="button" className="btn solid" onClick={() => go("decide")}>
            Record next step
          </button>
        </div>
        {caseQuery.isLoading && <p className="muted">Loading case…</p>}
        {caseQuery.error && <p className="error-text">{(caseQuery.error as Error).message}</p>}
        {data && (
          <>
            <div className="chip-row">
              <LaneBadge lane={data.lane} />
              <StatusBadge status={data.status} />
              <HarmBadge harm={data.harm} />
              <span className={`sla-chip sla-${screeningTone(data.screening_days_left)}`}>
                {screeningLabel(data.screening_days_left)}
              </span>
              <span className="muted">
                Owner {data.assignee_id === user.id ? "you" : data.assignee_id ?? "unassigned"}
              </span>
              {data.member_unmask_permitted && (
                <label className="unmask">
                  <input
                    type="checkbox"
                    checked={unmask}
                    onChange={(e) => setUnmask(e.target.checked)}
                  />
                  Reveal names
                </label>
              )}
            </div>
            <dl className="ws-metrics">
              <div>
                <dt>P(confirm)</dt>
                <dd className="mono">{pct(data.p_confirm)}</dd>
              </div>
              <div>
                <dt>Flagged</dt>
                <dd className="mono dollars">{money(data.flagged_dollars)}</dd>
              </div>
              <div>
                <dt>Members</dt>
                <dd className="mono">{data.members_affected}</dd>
              </div>
              <div>
                <dt>Hours</dt>
                <dd className="mono">{hours(data.estimated_hours)}</dd>
              </div>
              <div>
                <dt>Evidence</dt>
                <dd>
                  <EvidenceBar value={data.evidence_strength} />
                </dd>
              </div>
            </dl>
          </>
        )}
      </header>

      <nav className="ws-menu" aria-label="Case sections">
        {menu.map((item) => (
          <button
            key={item.id}
            type="button"
            className={tab === item.id ? "on" : ""}
            aria-current={tab === item.id ? "page" : undefined}
            onClick={() => go(item.id)}
          >
            {item.label}
            {typeof item.count === "number" ? (
              <span className="mono">{item.count}</span>
            ) : null}
          </button>
        ))}
      </nav>

      <div className={`ws-stage ${tab === "claims" || tab === "network" ? "is-wide" : ""}`}>
        <div className="ws-stage-inner">
          {tab === "overview" && data && (
            <section className="ws-overview" aria-labelledby="overview-title">
              <h2 id="overview-title">Case overview</h2>
              {data.why_rank?.text && <p className="why-rank">{data.why_rank.text}</p>}
              {data.recommendation === "tracked_backlog" && (
                <p className="muted">
                  Outside today&apos;s recommended desk. Still open for reassessment.
                </p>
              )}
              <div className="rank-block">
                <p className="kicker">Why it ranked here</p>
                <FactorBars factors={data.rank_factors} />
              </div>
              <dl className="facts dense">
                <div>
                  <dt>Expected value</dt>
                  <dd className="mono">{money(data.expected_value ?? 0)}</dd>
                </div>
                <div>
                  <dt>Severity</dt>
                  <dd className="mono">{data.severity}</dd>
                </div>
                <div>
                  <dt>F30 / F60 / F90</dt>
                  <dd className="mono">
                    {pct(data.f30)} · {pct(data.f60)} · {pct(data.f90)}
                  </dd>
                </div>
                <div>
                  <dt>Status</dt>
                  <dd>{data.status}</dd>
                </div>
              </dl>
              {data.entity_ids && data.entity_ids.length > 1 && (
                <p className="muted">
                  Network NPIs: <span className="mono">{data.entity_ids.join(" · ")}</span>
                </p>
              )}
              <p className="note">
                Ranked suspicion for human review. The model does not print fraud on a provider.
                Member names stay masked unless you reveal them from the header.
              </p>
            </section>
          )}

          {tab === "findings" && data && (
            <FindingsPanel alerts={data.alerts} onOpen={(id) => setItemId(`alert:${id}`)} />
          )}

          {tab === "brief" && (
            <BriefPanel
              brief={briefQuery.data}
              loading={briefQuery.isLoading}
              error={err(briefQuery)}
              onCite={openCite}
            />
          )}

          {tab === "claims" && (
            <ClaimsTable
              pack={claimsQuery.data}
              loading={claimsQuery.isLoading}
              error={err(claimsQuery)}
              onOpenLine={openLine}
            />
          )}

          {tab === "timeline" && (
            <TimelinePanel
              events={timelineQuery.data?.events}
              loading={timelineQuery.isLoading}
              error={err(timelineQuery)}
              onOpen={openRef}
            />
          )}

          {tab === "network" && (
            <NetworkPanel
              pack={networkQuery.data}
              loading={networkQuery.isLoading}
              error={err(networkQuery)}
              onSelect={onNode}
            />
          )}

          {tab === "decide" && (
            <DecisionBar
              disabled={!canDecide || closed}
              gaps={data?.evidence_gaps ?? briefQuery.data?.evidence_gaps ?? []}
              pending={decideMut.isPending}
              error={
                decideMut.error
                  ? decideMut.error instanceof ApiError
                    ? decideMut.error.message
                    : (decideMut.error as Error).message
                  : !canDecide
                    ? "Your role cannot record a case decision."
                    : closed
                      ? `Case is already ${data?.status}.`
                      : null
              }
              result={decideMut.data ?? null}
              existingProposal={data?.latest_proposal ?? null}
              alerts={data?.alerts ?? []}
              onSubmit={(action, reason, evidenceRefs, ladderStep) =>
                decideMut.mutate({
                  action,
                  reason,
                  evidence_refs: evidenceRefs,
                  ladder_step: ladderStep,
                })
              }
            />
          )}
        </div>
      </div>

      {itemId && (
        <EvidenceDrawer caseId={caseId} itemId={itemId} onClose={() => setItemId(null)} />
      )}
    </main>
  );
}
