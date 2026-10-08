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
import { FactorBars } from "../queue/FactorBars";
import { BriefPanel } from "./BriefPanel";
import { CaseHeader } from "./CaseHeader";
import { ClaimsTable } from "./ClaimsTable";
import { DecisionBar } from "./DecisionBar";
import type { DecisionAction } from "./decisionConfig";
import { EvidenceDrawer } from "./EvidenceDrawer";
import { FindingsPanel } from "./FindingsPanel";
import { focusMatches, type EntityFocus } from "./focus";
import { NetworkPanel, type JumpTarget } from "./NetworkPanel";
import { CaseLineage } from "./ProvenancePanel";
import { TimelinePanel } from "./TimelinePanel";
import "./workspace.css";

/** Sections in reading order; ids double as URL hashes. */
const SECTIONS = [
  { id: "evidence", label: "Evidence" },
  { id: "network", label: "Network" },
  { id: "claims", label: "Claims" },
  { id: "brief", label: "Brief" },
  { id: "decide", label: "Decision" },
] as const;

/** Hashes from the earlier tabbed workspace still land on the right section. */
const LEGACY_HASH: Record<string, string> = { overview: "evidence", findings: "evidence", timeline: "claims" };

export function WorkspacePage() {
  const { caseId } = useParams({ from: "/investigator/workspace/$caseId" });
  const { user } = useAuth();
  const queryClient = useQueryClient();
  const [unmask, setUnmask] = useState(false);
  const [itemId, setItemId] = useState<string | null>(null);
  const [selection, setSelection] = useState<GraphSelection | null>(null);

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
      void queryClient.invalidateQueries({ queryKey: ["queue"] });
      void queryClient.invalidateQueries({ queryKey: ["wiki-proposals"] });
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
    return node ? { id: node.id, type: node.type, label: node.label } : null;
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
  const jump = useCallback((target: JumpTarget) => {
    document.getElementById(target)?.scrollIntoView({ block: "start" });
  }, []);

  // Honour a section hash once the case has rendered (including legacy tab hashes).
  useEffect(() => {
    if (!data) return;
    const raw = window.location.hash.replace("#", "");
    const id = LEGACY_HASH[raw] ?? raw;
    if (id && SECTIONS.some((s) => s.id === id)) document.getElementById(id)?.scrollIntoView({ block: "start" });
  }, [data]);

  if (!user) return null;
  if (!canRead) {
    return (
      <main id="main" className="page">
        <PageHeader eyebrow="Investigation" title="Investigation workspace" />
        <ErrorState title="Access denied" error="Your role cannot read cases." />
      </main>
    );
  }

  const closed = Boolean(data && data.status !== "open");
  const decisionError = decideMut.error
    ? decideMut.error instanceof ApiError
      ? decideMut.error.message
      : (decideMut.error as Error).message
    : !canDecide
      ? "Your role cannot record a case decision."
      : closed
        ? `Case is already ${data?.status}.`
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
            unmask={unmask}
            onUnmaskChange={setUnmask}
          />

          <nav className="section-nav" aria-label="Case sections">
            <ol>
              {SECTIONS.map((section, i) => (
                <li key={section.id}>
                  <a href={`#${section.id}`}>
                    <span className="section-index" aria-hidden="true">
                      {i + 2}
                    </span>
                    {section.label}
                  </a>
                </li>
              ))}
            </ol>
            {focus ? (
              <p className="focus-chip" role="status">
                Focused on <strong>{focus.label}</strong>
                <button type="button" className="btn small ghost" onClick={clearFocus}>
                  Clear
                </button>
              </p>
            ) : null}
          </nav>

          <Panel
            id="evidence"
            eyebrow="2 · Evidence"
            title="Why this case was surfaced"
            description={data.why_rank?.text}
          >
            <div className="evidence-grid">
              <FactorBars factors={data.rank_factors} />
              <div className="evidence-summary subpanel">
                {data.grouping ? (
                  <>
                    <h3>Grouped alerts</h3>
                    <p>{data.grouping.text}</p>
                    <p className="muted">
                      {data.grouping.alert_count} alert{data.grouping.alert_count === 1 ? "" : "s"} across{" "}
                      {data.grouping.entity_ids.length} NPI{data.grouping.entity_ids.length === 1 ? "" : "s"}
                    </p>
                  </>
                ) : null}
                {data.evidence_gaps && data.evidence_gaps.length > 0 ? (
                  <>
                    <h3>Evidence still needed</h3>
                    <ul className="compact-list">
                      {data.evidence_gaps.map((gap) => (
                        <li key={gap}>{gap}</li>
                      ))}
                    </ul>
                  </>
                ) : null}
                <p className="note">
                  Ranked suspicion for human review. The model does not label a provider as fraudulent.
                </p>
              </div>
            </div>
            <FindingsPanel
              alerts={data.alerts}
              focusAlertIds={matches?.alertIds ?? null}
              focusLabel={focus?.label ?? null}
              onOpen={(alertId) => setItemId(`alert:${alertId}`)}
            />
            {data.provenance ? (
              <details className="lineage-details">
                <summary>How this case was built (evidence trail)</summary>
                <CaseLineage provenance={data.provenance} />
              </details>
            ) : null}
          </Panel>

          <NetworkPanel
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
          />

          <Panel
            id="claims"
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

          <Panel
            id="brief"
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

          <Panel
            id="decide"
            eyebrow="6 · Decision · human only"
            title="Record the next step"
            description="An alert is suspicion, not a confirmed finding of fraud. Cite the evidence you inspected and give a reason another reviewer can follow."
            className="decision-panel"
          >
            <DecisionBar
              disabled={!canDecide || closed}
              gaps={data.evidence_gaps ?? briefQuery.data?.evidence_gaps ?? []}
              pending={decideMut.isPending}
              error={decisionError}
              result={decideMut.data ?? null}
              existingProposal={data.latest_proposal ?? null}
              alerts={data.alerts}
              onSubmit={(action, reason, evidenceRefs, ladderStep) =>
                decideMut.mutate({ action, reason, evidence_refs: evidenceRefs, ladder_step: ladderStep })
              }
            />
          </Panel>
        </>
      ) : null}

      {itemId ? <EvidenceDrawer caseId={caseId} itemId={itemId} onClose={closeDrawer} /> : null}
    </main>
  );
}
