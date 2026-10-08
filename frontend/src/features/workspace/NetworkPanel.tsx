import { Suspense, lazy, useCallback, useMemo, useState } from "react";
import type { GraphControls } from "../../components/network/CaseNetworkGraph";
import { EdgeKindFilter, GraphLegend } from "../../components/network/GraphLegend";
import type { GraphModel } from "../../components/network/graphModel";
import { LinkedEntityList } from "../../components/network/LinkedEntityList";
import {
  edgeMeta,
  hopDistances,
  linkedEntities,
  networkSummary,
  nodeMeta,
  type GraphLayout,
  type GraphSelection,
  type LinkedEntity,
} from "../../components/network/networkModel";
import { HarmFlag, RiskLevelBadge } from "../../components/Badge";
import { Panel } from "../../components/ui/Panel";
import { EmptyState, ErrorState, LoadingState } from "../../components/ui/States";
import { count, money } from "../../lib/format";
import "../../components/network/network.css";

const CaseNetworkGraph = lazy(() => import("../../components/network/CaseNetworkGraph"));

export interface FocusCounts {
  lines: number;
  findings: number;
  citations: number;
}

export type JumpTarget = "evidence" | "claims" | "brief";

interface NetworkPanelProps {
  model: GraphModel | undefined;
  loading: boolean;
  error: unknown;
  onRetry: () => void;
  selection: GraphSelection | null;
  onSelect: (selection: GraphSelection | null) => void;
  focusCounts: FocusCounts | null;
  onJump: (target: JumpTarget) => void;
  onOpenProfile: (providerId: string) => void;
}

export function NetworkPanel(props: NetworkPanelProps) {
  const { model, loading, error, onRetry } = props;
  return (
    <Panel
      id="network"
      eyebrow="3 · Network"
      title="Who this provider is linked to"
      description="Two-hop neighbourhood from the extract: ownership, shared TIN and address, referrals, and the members and facilities on flagged claims."
      actions={
        model ? (
          <span className="badge">
            {count(model.nodes.length, "entity", "entities")} · {count(model.edges.length, "link")}
          </span>
        ) : null
      }
    >
      {loading ? <LoadingState label="Loading the case network…" /> : null}
      {error ? <ErrorState title="Network unavailable" error={error} onRetry={onRetry} /> : null}
      {model && model.nodes.length <= 1 ? (
        <EmptyState title="No linked entities">
          The extract has no ownership, TIN, address, referral or shared-claim links for this case subject.
        </EmptyState>
      ) : null}
      {model && model.nodes.length > 1 ? <NetworkExplorer {...props} model={model} /> : null}
    </Panel>
  );
}

function NetworkExplorer({
  model,
  selection,
  onSelect,
  focusCounts,
  onJump,
  onOpenProfile,
}: NetworkPanelProps & { model: GraphModel }) {
  const [enabled, setEnabled] = useState<Record<string, boolean>>({});
  const [layout, setLayout] = useState<GraphLayout>("organic");
  const [controls, setControls] = useState<GraphControls | null>(null);

  const edges = useMemo(() => model.edges.filter((edge) => enabled[edge.kind] !== false), [model, enabled]);
  // Entities left with no enabled link drop out of the graph and the list (the subject always stays).
  const visible = useMemo<GraphModel>(() => {
    const linked = new Set(edges.flatMap((edge) => [edge.source, edge.target]));
    return { ...model, nodes: model.nodes.filter((node) => node.isSubject || linked.has(node.id)) };
  }, [model, edges]);
  const hidden = model.nodes.length - visible.nodes.length;
  const hops = useMemo(() => hopDistances(visible, edges), [visible, edges]);
  const entities = useMemo(() => linkedEntities(visible, edges), [visible, edges]);
  const structural = model.edges.some((edge) => edgeMeta(edge.kind).family !== "claim");
  const summary = networkSummary(visible, edges);
  const onReady = useCallback((next: GraphControls) => setControls(next), []);
  const selectedNodeId = selection?.kind === "node" ? selection.id : null;

  return (
    <>
      <EdgeKindFilter
        edges={model.edges}
        enabled={enabled}
        onToggle={(kind, on) => setEnabled((prev) => ({ ...prev, [kind]: on }))}
      />
      {!structural ? (
        <p className="banner info">
          No ownership, TIN, address or referral links were found; providers here are linked only through shared
          members on flagged claims.
        </p>
      ) : null}
      <div className="graph-layout">
        <div className="graph-stage">
          <div className="graph-viewport">
            <div className="graph-controls" role="toolbar" aria-label="Graph view">
              <button
                type="button"
                className="btn"
                aria-label="Zoom in"
                title="Zoom in"
                disabled={!controls}
                onClick={() => controls?.zoomIn()}
              >
                +
              </button>
              <button
                type="button"
                className="btn"
                aria-label="Zoom out"
                title="Zoom out"
                disabled={!controls}
                onClick={() => controls?.zoomOut()}
              >
                −
              </button>
              <button
                type="button"
                className="btn"
                aria-label="Fit graph to view"
                title="Fit to view"
                disabled={!controls}
                onClick={() => controls?.fit()}
              >
                ⤢
              </button>
              <button
                type="button"
                className="btn"
                aria-label="Centre on case subject"
                title="Centre on case subject"
                disabled={!controls}
                onClick={() => controls?.focusSubject()}
              >
                ◎
              </button>
              <button
                type="button"
                className="btn"
                aria-label="Rings by hop distance"
                title="Rings by hop distance"
                aria-pressed={layout === "rings"}
                onClick={() => setLayout((prev) => (prev === "organic" ? "rings" : "organic"))}
              >
                ◍
              </button>
            </div>
            <div
              className="graph-canvas-wrap"
              role="img"
              aria-label={`Case network graph. ${summary} Use the linked entity list to explore it with a keyboard.`}
            >
              <Suspense fallback={<p className="graph-hint">Loading graph…</p>}>
                <CaseNetworkGraph
                  model={visible}
                  edges={edges}
                  hops={hops}
                  layout={layout}
                  selection={selection}
                  onSelect={onSelect}
                  onReady={onReady}
                />
              </Suspense>
            </div>
          </div>
          <GraphLegend nodes={visible.nodes} edges={edges} />
          {hidden > 0 ? (
            <p className="graph-hint">{count(hidden, "entity", "entities")} hidden: no links of the selected types.</p>
          ) : null}
          <p className="graph-hint" aria-hidden="true">
            Hover to highlight two hops · click a node or link · scroll to zoom · drag to pan
          </p>
        </div>
        <aside className="graph-side" aria-label="Network details">
          {selection ? (
            <SelectionCard
              selection={selection}
              entities={entities}
              subjectId={model.subjectId}
              focusCounts={focusCounts}
              onSelect={onSelect}
              onJump={onJump}
              onOpenProfile={onOpenProfile}
            />
          ) : (
            <p className="note">
              Select an entity or link to filter the claims, findings and brief citations to it.
            </p>
          )}
          <LinkedEntityList
            entities={entities}
            selectedId={selectedNodeId}
            onSelect={(id) => onSelect(selectedNodeId === id ? null : { kind: "node", id })}
          />
        </aside>
      </div>
      <p className="sr-only" aria-live="polite">
        {summary}
      </p>
    </>
  );
}

interface SelectionCardProps {
  selection: GraphSelection;
  entities: LinkedEntity[];
  subjectId: string;
  focusCounts: FocusCounts | null;
  onSelect: (selection: GraphSelection | null) => void;
  onJump: (target: JumpTarget) => void;
  onOpenProfile: (providerId: string) => void;
}

function SelectionCard({ selection, entities, subjectId, focusCounts, onSelect, onJump, onOpenProfile }: SelectionCardProps) {
  const byId = new Map(entities.map((e) => [e.node.id, e]));
  const focusId = selection.kind === "node" ? selection.id : selection.source === subjectId ? selection.target : selection.source;
  const entity = byId.get(focusId);
  if (!entity) return null;
  const node = entity.node;

  return (
    <section className="selection-card" aria-live="polite" aria-labelledby="selection-title">
      {selection.kind === "edge" ? (
        <div>
          <p className="kicker">{edgeMeta(selection.edgeKind).label} link</p>
          <p>{edgeMeta(selection.edgeKind).meaning}</p>
          <p className="muted">
            {byId.get(selection.source)?.node.label ?? selection.source}
            {selection.directed ? " → " : " ↔ "}
            {byId.get(selection.target)?.node.label ?? selection.target}
          </p>
        </div>
      ) : null}
      <div>
        <p className="kicker">
          {node.id === subjectId ? "Case subject" : nodeMeta(node.type).label}
          {entity.hop !== null && entity.hop > 0 ? ` · ${entity.hop} hop${entity.hop === 1 ? "" : "s"}` : ""}
        </p>
        <h3 id="selection-title">{node.label}</h3>
        <p className="mono muted">
          {node.id}
          {node.specialty ? ` · ${node.specialty.replaceAll("_", " ")}` : ""}
        </p>
        <p className="selection-badges">
          {node.riskLevel ? <RiskLevelBadge level={node.riskLevel} /> : null}
          {node.harm !== null ? <HarmFlag harm={node.harm} /> : null}
          {node.inCase ? <span className="badge">In this case</span> : <span className="badge">Context</span>}
        </p>
      </div>
      {node.flaggedPaid !== null || node.alertIds.length > 0 ? (
        <dl className="facts compact">
          {node.flaggedPaid !== null ? (
            <div>
              <dt>Flagged paid</dt>
              <dd className="num">
                {money(node.flaggedPaid)} · {count(node.flaggedLines ?? 0, "line")}
              </dd>
            </div>
          ) : null}
          {node.alertIds.length > 0 ? (
            <div>
              <dt>Alerts</dt>
              <dd className="num">{node.alertIds.length}</dd>
            </div>
          ) : null}
        </dl>
      ) : null}
      {entity.relations.length > 0 ? <ConnectionCounts entity={entity} /> : null}
      {entity.relations.length > 0 ? (
        <ul className="relation-list">
          {entity.relations.slice(0, 6).map((relation) => (
            <li key={`${relation.kind}-${relation.other.id}-${relation.direction}`}>
              {edgeMeta(relation.kind).label}
              {relation.direction === "out" ? " → " : relation.direction === "in" ? " ← " : " · "}
              <button type="button" className="link-button" onClick={() => onSelect({ kind: "node", id: relation.other.id })}>
                {relation.other.label}
              </button>
            </li>
          ))}
          {entity.relations.length > 6 ? <li className="muted">+{entity.relations.length - 6} more links</li> : null}
        </ul>
      ) : null}
      {focusCounts ? (
        <div className="selection-actions">
          <button type="button" className="btn small solid" disabled={focusCounts.lines === 0} onClick={() => onJump("claims")}>
            {count(focusCounts.lines, "claim line")}
          </button>
          <button type="button" className="btn small" disabled={focusCounts.findings === 0} onClick={() => onJump("evidence")}>
            {count(focusCounts.findings, "finding")}
          </button>
          <button type="button" className="btn small" disabled={focusCounts.citations === 0} onClick={() => onJump("brief")}>
            {count(focusCounts.citations, "brief citation")}
          </button>
          {node.type === "provider" ? (
            <button type="button" className="btn small ghost" onClick={() => onOpenProfile(node.id)}>
              Provider profile
            </button>
          ) : null}
        </div>
      ) : null}
      {focusCounts && focusCounts.lines === 0 && focusCounts.findings === 0 ? (
        <p className="muted">
          No flagged claim lines or findings on this case involve this entity. The API does not yet return claims for
          linked providers outside the case.
        </p>
      ) : null}
      <button type="button" className="link-button" onClick={() => onSelect(null)}>
        Clear selection
      </button>
    </section>
  );
}

/** "Connections": link counts by kind for the selected entity. */
function ConnectionCounts({ entity }: { entity: LinkedEntity }) {
  const byKind = new Map<string, number>();
  for (const relation of entity.relations) byKind.set(relation.kind, (byKind.get(relation.kind) ?? 0) + 1);
  return (
    <p className="muted">
      Connections:{" "}
      {[...byKind.entries()].map(([kind, n]) => `${edgeMeta(kind).label} ${n}`).join(" · ")}
    </p>
  );
}
