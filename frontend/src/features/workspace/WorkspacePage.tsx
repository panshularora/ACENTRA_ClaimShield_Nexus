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

export function WorkspacePage() {
  const { caseId } = useParams({ from: "/investigator/workspace/$caseId" });
  const { user } = useAuth();
  const queryClient = useQueryClient();
  const [unmask, setUnmask] = useState(false);
  const [itemId, setItemId] = useState<string | null>(null);

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

  return (
    <main id="main" className="workspace">
      <section className="ws-panel ws-summary" aria-labelledby="sum-title">
        <header className="ws-panel-head">
          <div>
            <p className="kicker">Investigation · suspicion only</p>
            <h1 id="sum-title">
              {data?.primary_entity?.name ?? caseId}
            </h1>
            <p className="mono muted">{caseId}</p>
          </div>
          <Link to="/investigator/cases" className="btn ghost">
            Worklist
          </Link>
        </header>
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
            </div>
            {data.why_rank?.text && <p className="why-rank">{data.why_rank.text}</p>}
            {data.recommendation === "tracked_backlog" && (
              <p className="muted">Outside today&apos;s recommended desk. Still open for reassessment.</p>
            )}
            <FactorBars factors={data.rank_factors} />
            <p className="entity-line">
              <span className="mono">{data.primary_entity_id}</span>
              {data.primary_entity?.specialty && (
                <span className="muted">{data.primary_entity.specialty}</span>
              )}
              {data.primary_entity?.kind && (
                <span className="muted">{data.primary_entity.kind}</span>
              )}
            </p>
            {data.entity_ids && data.entity_ids.length > 1 && (
              <p className="muted">
                Network NPIs:{" "}
                <span className="mono">{data.entity_ids.join(" · ")}</span>
              </p>
            )}
            <dl className="facts dense">
              <div>
                <dt>Status</dt>
                <dd>{data.status}</dd>
              </div>
              <div>
                <dt>P(confirm)</dt>
                <dd className="mono">{pct(data.p_confirm)}</dd>
              </div>
              <div>
                <dt>Expected value</dt>
                <dd className="mono">{money(data.expected_value ?? 0)}</dd>
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
                <dt>Severity</dt>
                <dd className="mono">{data.severity}</dd>
              </div>
              <div>
                <dt>Hours</dt>
                <dd className="mono">{hours(data.estimated_hours)}</dd>
              </div>
              <div>
                <dt>F30 / F60 / F90</dt>
                <dd className="mono">
                  {pct(data.f30)} · {pct(data.f60)} · {pct(data.f90)}
                </dd>
              </div>
              <div>
                <dt>Evidence</dt>
                <dd>
                  <EvidenceBar value={data.evidence_strength} />
                </dd>
              </div>
            </dl>
            <div>
              <p className="kicker">Triggered signals</p>
              {data.alerts.length === 0 ? (
                <p className="muted">No alerts attached.</p>
              ) : (
                <ul className="signal-list compact">
                  {data.alerts.map((alert) => (
                    <li key={alert.alert_id}>
                      <button
                        type="button"
                        className="linkish"
                        onClick={() => setItemId(`alert:${alert.alert_id}`)}
                      >
                        <span className="mono">{alert.rule_id ?? alert.detector}</span>
                        <span>{alert.label ?? alert.detector}</span>
                        {alert.policy_ref && <span className="muted">Policy {alert.policy_ref}</span>}
                        <span className="muted">{alert.line_ids.length} lines</span>
                      </button>
                    </li>
                  ))}
                </ul>
              )}
            </div>
            <p className="note">
              Ranked suspicion for human review. The model does not print fraud on a provider.
            </p>
            <p className="owner-line">
              <span>Owner {data.assignee_id === user.id ? "you" : data.assignee_id ?? "unassigned"}</span>
              {canAssign && data.assignee_id !== user.id && (
                <button
                  type="button"
                  className="btn ghost"
                  disabled={assignMut.isPending}
                  onClick={() => assignMut.mutate()}
                >
                  {assignMut.isPending ? "Taking…" : "Take ownership"}
                </button>
              )}
            </p>
            <FindingsPanel alerts={data.alerts} onOpen={(id) => setItemId(`alert:${id}`)} />
            {data.member_unmask_permitted && (
              <label className="unmask">
                <input
                  type="checkbox"
                  checked={unmask}
                  onChange={(e) => setUnmask(e.target.checked)}
                />
                Reveal member names. Writes a member.unmask audit event (HIPAA minimum necessary).
              </label>
            )}
          </>
        )}
      </section>

      <BriefPanel
        brief={briefQuery.data}
        loading={briefQuery.isLoading}
        error={err(briefQuery)}
        onCite={openCite}
      />
      <ClaimsTable
        pack={claimsQuery.data}
        loading={claimsQuery.isLoading}
        error={err(claimsQuery)}
        onOpenLine={openLine}
      />
      <TimelinePanel
        events={timelineQuery.data?.events}
        loading={timelineQuery.isLoading}
        error={err(timelineQuery)}
        onOpen={openRef}
      />
      <NetworkPanel
        pack={networkQuery.data}
        loading={networkQuery.isLoading}
        error={err(networkQuery)}
        onSelect={onNode}
      />
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

      {itemId && (
        <EvidenceDrawer caseId={caseId} itemId={itemId} onClose={() => setItemId(null)} />
      )}
    </main>
  );
}
