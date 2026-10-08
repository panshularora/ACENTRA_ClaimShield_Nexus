import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { useParams } from "@tanstack/react-router";
import { useCallback, useEffect, useMemo, useState } from "react";
import { api, ApiError, can } from "../../api/client";
import type { Cite } from "../../api/types";
import { useAuth } from "../../auth/AuthProvider";
import { normalizeNetwork } from "../../components/network/graphModel";
import type { GraphSelection } from "../../components/network/networkModel";
import { PageHeader } from "../../components/ui/PageHeader";
import { Panel } from "../../components/ui/Panel";
import { NotFound } from "../../components/ui/NotFound";
import { ErrorState, LoadingState } from "../../components/ui/States";
import { pct } from "../../lib/format";
import { FactorBars } from "../queue/FactorBars";
import { BriefPanel } from "./BriefPanel";
import { CaseHeader, FactorList } from "./CaseHeader";
import { ClaimsTable } from "./ClaimsTable";
import { DecisionBar } from "./DecisionBar";
import { configsFromOptions, type DecisionAction } from "./decisionConfig";
import { EvidenceDrawer } from "./EvidenceDrawer";
import { FindingsPanel } from "./FindingsPanel";
import { focusMatches, type EntityFocus } from "./focus";
import { NetworkPanel, type JumpTarget } from "./NetworkPanel";
import { CaseLineage } from "./ProvenancePanel";
import { TimelinePanel } from "./TimelinePanel";
import "./workspace.css";

/** Tabs 2–6; ids double as URL hashes. */
const SECTIONS = [
  { id: "evidence", label: "Evidence" },
  { id: "network", label: "Network" },
  { id: "claims", label: "Claims" },
  { id: "brief", label: "Brief" },
  { id: "decide", label: "Decision" },
] as const;

type SectionId = (typeof SECTIONS)[number]["id"];

/** Hashes from the earlier long-scroll workspace still land on the right tab. */
const LEGACY_HASH: Record<string, SectionId> = { overview: "evidence", findings: "evidence", timeline: "claims" };

function sectionFromHash(): SectionId {
  const raw = window.location.hash.replace("#", "");
  const mapped = LEGACY_HASH[raw] ?? raw;
  return SECTIONS.some((section) => section.id === mapped) ? (mapped as SectionId) : "evidence";
}

export function WorkspacePage() {
  const { caseId } = useParams({ from: "/investigator/workspace/$caseId" });
  const { user } = useAuth();
  const queryClient = useQueryClient();
  const [unmask, setUnmask] = useState(false);
  const [itemId, setItemId] = useState<string | null>(null);
  const [selection, setSelection] = useState<GraphSelection | null>(null);
  const [tab, setTab] = useState<SectionId>(sectionFromHash);

  const canRead = can(user, "case:read");
  const canDecide = can(user, "case:decide");
  const canAssign = can(user, "case:assign");

  const caseQuery = useQuery({ queryKey: ["case", caseId], queryFn: () => api.getCase(caseId), enabled: canRead });
  // Everything else waits for the case, so an unknown case id costs one request (a 404, not retried).
  const caseLoaded = caseQuery.isSuccess;
  const briefQuery = useQuery({ queryKey: ["brief", caseId], queryFn: () => api.getBrief(caseId), enabled: caseLoaded });
  const claimsQuery = useQuery({
    queryKey: ["claims", caseId, unmask],
    queryFn: () => api.getClaims(caseId, unmask),
    enabled: caseLoaded,
  });
  const timelineQuery = useQuery({
    queryKey: ["timeline", caseId, unmask],
    queryFn: () => api.getTimeline(caseId, unmask),
    enabled: caseLoaded,
  });
  const networkQuery = useQuery({
    queryKey: ["network", caseId, unmask],
    queryFn: () => api.getNetwork(caseId, 2, unmask),
    enabled: caseLoaded,
  });
  const optionsQuery = useQuery({
    queryKey: ["decision-options", caseId],
    queryFn: () => api.getDecisionOptions(caseId),
    enabled: caseLoaded,
  });

  const assignMut = useMutation({
    mutationFn: () => api.assignCase(caseId),
    onSuccess: () => {
      void queryClient.invalidateQueries({ queryKey: ["case", caseId] });
      void queryClient.invalidateQueries({ queryKey: ["queue"] });
    },
  });

  const decideMut = useMutation({
    mutationFn: (vars: { action: DecisionAction; reason: string; ladder_step?: string | null; evidence_refs?: string[] }) =>
      api.decide(caseId, vars),
    onSuccess: () => {
      void queryClient.invalidateQueries({ queryKey: ["case", caseId] });
      void queryClient.invalidateQueries({ queryKey: ["brief", caseId] });
      void queryClient.invalidateQueries({ queryKey: ["decision-options", caseId] });
      void queryClient.invalidateQueries({ queryKey: ["queue"] });
      void queryClient.invalidateQueries({ queryKey: ["wiki-proposals"] });
      void queryClient.invalidateQueries({ queryKey: ["case-history"] });
    },
  });
  const reviewMut = useMutation({
    mutationFn: (vars: { kind: "approve" | "reject"; note: string; decisionId: string }) =>
      vars.kind === "approve" ? api.approveDecision(vars.decisionId, vars.note) : api.rejectDecision(vars.decisionId, vars.note),
    onSuccess: () => {
      void queryClient.invalidateQueries({ queryKey: ["case", caseId] });
      void queryClient.invalidateQueries({ queryKey: ["brief", caseId] });
      void queryClient.invalidateQueries({ queryKey: ["decision-options", caseId] });
      void queryClient.invalidateQueries({ queryKey: ["queue"] });
      void queryClient.invalidateQueries({ queryKey: ["wiki-proposals"] });
      void queryClient.invalidateQueries({ queryKey: ["case-history"] });
    },
  });
  const reopenMut = useMutation({
    mutationFn: (reason: string) => api.reopenCase(caseId, reason),
    onSuccess: () => {
      void queryClient.invalidateQueries({ queryKey: ["case", caseId] });
      void queryClient.invalidateQueries({ queryKey: ["decision-options", caseId] });
      void queryClient.invalidateQueries({ queryKey: ["queue"] });
      void queryClient.invalidateQueries({ queryKey: ["case-history"] });
    },
  });

  const data = caseQuery.data;
  const pack = networkQuery.data;
  const claimRows = claimsQuery.data?.rows;
  const network = useMemo(
    () =>
      pack
        ? normalizeNetwork(pack, {
            caseEntityIds: data?.entity_ids,
            alerts: data?.alerts,
            rows: claimRows,
            subjectSeverity: data?.severity,
            subjectHarm: data?.harm,
          })
        : undefined,
    [pack, data, claimRows],
  );

  // Network selection → the entity every other section filters to.
  const focus = useMemo<EntityFocus | null>(() => {
    if (!selection || !network) return null;
    const id =
      selection.kind === "node"
        ? selection.id
        : selection.source === network.subjectId
          ? selection.target
          : selection.source;
    const node = network.nodes.find((n) => n.id === id);
    if (!node) return null;
    if (selection.kind === "edge") {
      const edge =
        network.edges.find((item) => item.id === selection.key) ??
        network.edges.find(
          (item) => item.source === selection.source && item.target === selection.target && item.kind === selection.edgeKind,
        );
      return {
        id: node.id,
        type: node.type,
        label: node.label,
        evidenceIds: edge ? [...edge.evidenceIds, `edge:${edge.id}`] : undefined,
        extraLineIds: edge?.evidence?.line_ids,
        extraAlertIds: edge?.evidence?.alert_ids,
      };
    }
    return { id: node.id, type: node.type, label: node.label, extraAlertIds: node.alertIds };
  }, [selection, network]);

  const matches = useMemo(
    () => (focus ? focusMatches(focus, claimsQuery.data?.rows ?? [], data?.alerts ?? [], network) : null),
    [focus, claimsQuery.data, data, network],
  );

  const citeMatches = useMemo(() => {
    if (!matches || !briefQuery.data) return 0;
    return briefQuery.data.sections
      .flatMap((section) => section.sentences)
      .filter((sentence) => sentence.cites.some((cite) => matches.citeIds.has(cite.id))).length;
  }, [matches, briefQuery.data]);

  const openCite = useCallback((cite: Cite) => setItemId(cite.id), []);
  const openRef = useCallback((ref: string) => setItemId(ref), []);
  const openLine = useCallback((lineId: string) => setItemId(`line:${lineId}`), []);
  const openProfile = useCallback((providerId: string) => setItemId(`provider:${providerId}`), []);
  const closeDrawer = useCallback(() => setItemId(null), []);
  const clearFocus = useCallback(() => setSelection(null), []);
  const openTab = useCallback((id: SectionId) => {
    setTab(id);
    const hash = `#${id}`;
    if (window.location.hash !== hash) history.replaceState(null, "", hash);
  }, []);

  const jump = useCallback(
    (target: JumpTarget) => {
      openTab(target);
    },
    [openTab],
  );

  useEffect(() => {
    setTab(sectionFromHash());
  }, [caseId]);

  if (!user) return null;
  if (!canRead) {
    return (
      <main id="main" className="page">
        <PageHeader eyebrow="Investigation" title="Investigation workspace" />
        <ErrorState title="Access denied" error="Your role cannot read cases." />
      </main>
    );
  }

  const options = optionsQuery.data;
  const decisionActions = options ? configsFromOptions(options.options) : undefined;
  const canRecord = options?.can_decide ?? (canDecide && data?.status === "open");
  const reviewError = reviewMut.error ?? reopenMut.error;
  const decisionError = decideMut.error
    ? decideMut.error instanceof ApiError
      ? decideMut.error.message
      : (decideMut.error as Error).message
    : reviewError
      ? reviewError instanceof ApiError
        ? reviewError.message
        : (reviewError as Error).message
      : !canDecide && !options?.can_approve && !options?.can_reopen
        ? "Your role cannot record a case decision."
        : options?.blocked_reason && !options.can_approve && !options.can_reopen
          ? options.blocked_reason
          : null;

  return (
    <main id="main" className="page workspace">
      {caseQuery.isLoading ? <LoadingState label="Loading case…" /> : null}
      {caseQuery.error instanceof ApiError && caseQuery.error.status === 404 ? (
        <NotFound title="Case not found">
          <p>
            No case <code>{caseId}</code> exists in the current detection run. It may belong to an earlier run, or the
            link may be mistyped.
          </p>
        </NotFound>
      ) : caseQuery.error ? (
        <ErrorState title="Case unavailable" error={caseQuery.error} onRetry={() => void caseQuery.refetch()} />
      ) : null}
      {data ? (
        <>
          <CaseHeader
            data={data}
            user={user}
            canAssign={canAssign}
            assigning={assignMut.isPending}
            onAssign={() => assignMut.mutate()}
            onDecide={() => openTab("decide")}
            unmask={unmask}
            onUnmaskChange={setUnmask}
          />

          <nav className="section-nav" aria-label="Case file">
            <div className="section-tabs" role="tablist">
              {SECTIONS.map((section, i) => (
                <button
                  key={section.id}
                  type="button"
                  role="tab"
                  id={`tab-${section.id}`}
                  aria-selected={tab === section.id}
                  aria-controls={section.id}
                  className={tab === section.id ? "is-active" : undefined}
                  onClick={() => openTab(section.id)}
                >
                  <span className="section-index" aria-hidden="true">
                    {i + 2}
                  </span>
                  {section.label}
                </button>
              ))}
            </div>
            {focus ? (
              <p className="focus-chip" role="status">
                Focused on <strong>{focus.label}</strong>
                <button type="button" className="btn small ghost" onClick={clearFocus}>
                  Clear
                </button>
              </p>
            ) : null}
          </nav>

          {tab === "evidence" ? (
            <Panel
              id="evidence"
              className="workspace-tab"
              eyebrow="2 · Evidence"
              title="Why this case is on the desk"
              description={data.why_rank?.text}
            >
              <dl className="evidence-dossier facts dense">
                <div>
                  <dt>Patterns on this file</dt>
                  <dd>{data.alerts.length}</dd>
                </div>
                <div>
                  <dt>Paid claim lines cited</dt>
                  <dd>{new Set(data.alerts.flatMap((alert) => alert.line_ids)).size}</dd>
                </div>
                <div>
                  <dt>Evidence strength</dt>
                  <dd>{pct(data.evidence_strength)}</dd>
                </div>
                <div>
                  <dt>Tables behind the packet</dt>
                  <dd>{data.provenance?.data_sources.length ?? "—"}</dd>
                </div>
              </dl>
              <p className="note">
                Each card below is a suspicion to verify: plain words first, then the detector, rule id, and
                tables. This packet is not a fraud label.
              </p>
              <div className="evidence-grid">
                <FactorBars factors={data.rank_factors} suspicion={data.p_confirm} title="How desk rank is built" />
                <div className="evidence-summary subpanel">
                  {data.grouping ? (
                    <>
                      <h3>Why these patterns sit together</h3>
                      <p>{data.grouping.text}</p>
                      <p className="muted">
                        {data.grouping.alert_count} pattern{data.grouping.alert_count === 1 ? "" : "s"} across{" "}
                        {data.grouping.entity_ids.length} provider{data.grouping.entity_ids.length === 1 ? "" : "s"}
                      </p>
                    </>
                  ) : null}
                  {data.evidence_gaps && data.evidence_gaps.length > 0 ? (
                    <>
                      <h3>What to collect next</h3>
                      <ul className="compact-list">
                        {data.evidence_gaps.map((gap) => (
                          <li key={gap}>{gap}</li>
                        ))}
                      </ul>
                    </>
                  ) : null}
                  <p className="note">
                    Ranked for a person to review. Scores do not close the case.
                  </p>
                </div>
              </div>
              {(data.risk_factors && data.risk_factors.length > 0) ||
              (data.p_confirm_factors && data.p_confirm_factors.length > 0) ? (
                <div className="case-model-factors">
                  <FactorList title="What is pushing 30-day suspicion" factors={data.risk_factors} />
                  <FactorList title="What is pushing the suspicion score" factors={data.p_confirm_factors} />
                </div>
              ) : null}
              <FindingsPanel
                alerts={data.alerts}
                focusAlertIds={matches?.alertIds ?? null}
                focusLabel={focus?.label ?? null}
                onOpen={(alertId) => setItemId(`alert:${alertId}`)}
              />
              {data.provenance ? (
                <details className="lineage-details">
                  <summary>How this case was built</summary>
                  <CaseLineage provenance={data.provenance} />
                </details>
              ) : null}
            </Panel>
          ) : null}

          {tab === "network" ? (
            <NetworkPanel
              caseId={caseId}
              unmask={unmask}
              model={network}
              loading={networkQuery.isLoading}
              error={networkQuery.error}
              onRetry={() => void networkQuery.refetch()}
              selection={selection}
              onSelect={setSelection}
              focusCounts={
                matches ? { lines: matches.lineIds.size, findings: matches.alertIds.size, citations: citeMatches } : null
              }
              onJump={jump}
              onOpenProfile={openProfile}
              onOpenEvidence={openRef}
            />
          ) : null}

          {tab === "claims" ? (
            <Panel
              id="claims"
              className="workspace-tab"
              eyebrow="4 · Claims"
              title="Flagged claims and billing over time"
              description="Claim lines attached to this case's alerts, from the adjudicated extract."
            >
              <TimelinePanel
                rows={claimsQuery.data?.rows}
                events={timelineQuery.data?.events}
                subjectId={data.primary_entity_id}
                loading={claimsQuery.isLoading || timelineQuery.isLoading}
                error={claimsQuery.error ?? timelineQuery.error}
                onOpen={openRef}
              />
              <ClaimsTable
                pack={claimsQuery.data}
                loading={claimsQuery.isLoading}
                error={claimsQuery.error}
                onOpenLine={openLine}
                focusLineIds={matches?.lineIds ?? null}
                focusLabel={focus?.label ?? null}
                onClearFocus={clearFocus}
              />
            </Panel>
          ) : null}

          {tab === "brief" ? (
            <Panel
              id="brief"
              className="workspace-tab"
              eyebrow="5 · Brief"
              title="Investigation brief"
              description="Every sentence cites the alert, claim or metric it came from. Select a citation to trace it."
            >
              <BriefPanel
                brief={briefQuery.data}
                loading={briefQuery.isLoading}
                error={briefQuery.error}
                onCite={openCite}
                highlightCiteIds={matches?.citeIds ?? null}
                focusLabel={focus?.label ?? null}
              />
            </Panel>
          ) : null}

          {tab === "decide" ? (
            <Panel
              id="decide"
              eyebrow="6 · Decision · human only"
              title="Record the next step"
              description="Write what you checked and why. Another reviewer should be able to follow the same claims."
              className="decision-panel workspace-tab"
            >
              <DecisionBar
                actions={decisionActions}
                minReasonChars={options?.min_reason_chars}
                disabled={!canRecord}
                blockedReason={options?.blocked_reason}
                gaps={data.evidence_gaps ?? briefQuery.data?.evidence_gaps ?? []}
                pending={decideMut.isPending}
                error={decisionError}
                result={decideMut.data ?? null}
                existingProposal={data.latest_proposal ?? null}
                alerts={data.alerts}
                pendingDecision={options?.pending_decision ?? data.pending_decision}
                canApprove={options?.can_approve}
                canReopen={options?.can_reopen}
                reviewPending={reviewMut.isPending || reopenMut.isPending}
                onSubmit={(action, reason, evidenceRefs, ladderStep) =>
                  decideMut.mutate({ action, reason, evidence_refs: evidenceRefs, ladder_step: ladderStep })
                }
                onApprove={(note) => {
                  const id = (options?.pending_decision ?? data.pending_decision)?.decision_id;
                  if (id) reviewMut.mutate({ kind: "approve", note, decisionId: id });
                }}
                onReject={(note) => {
                  const id = (options?.pending_decision ?? data.pending_decision)?.decision_id;
                  if (id) reviewMut.mutate({ kind: "reject", note, decisionId: id });
                }}
                onReopen={(reason) => reopenMut.mutate(reason)}
              />
            </Panel>
          ) : null}
        </>
      ) : null}

      {itemId ? <EvidenceDrawer caseId={caseId} itemId={itemId} onClose={closeDrawer} /> : null}
    </main>
  );
}
