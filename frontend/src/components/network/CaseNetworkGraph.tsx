import cytoscape from "cytoscape";
import fcose, { type FcoseLayoutOptions } from "cytoscape-fcose";
import { useEffect, useLayoutEffect, useRef } from "react";
import { token } from "../../lib/theme";
import type { GraphEdge, GraphModel } from "./graphModel";
import { graphStyles } from "./graphStyles";
import { edgeHoverLabel, edgeMeta, type GraphLayout, type GraphSelection } from "./networkModel";
import { nodeIcon } from "./nodeIcons";

cytoscape.use(fcose);

/** Ring order inside each hop (design system §7.6). */
const TYPE_ORDER = ["owner", "facility", "provider", "address", "phone", "bank", "member"];
/** Small graphs label every node (§7.5). */
const LABEL_ALL_BELOW = 12;

function toElements(model: GraphModel, edges: GraphEdge[]): cytoscape.ElementDefinition[] {
  const glyph = token("--graph-node-glyph");
  const subjectGlyph = token("--graph-subject-glyph");
  const labelAll = model.nodes.length <= LABEL_ALL_BELOW;
  const nodes: cytoscape.ElementDefinition[] = model.nodes.map((node) => ({
    group: "nodes",
    data: {
      id: node.id,
      type: node.type,
      label: node.label,
      short: node.short,
      risk: node.riskLevel,
      harm: (node.harm ?? 0) >= 3,
      inCase: node.inCase && node.type !== "member",
      icon: nodeIcon(node.type, node.isSubject ? subjectGlyph : glyph),
    },
    classes: [node.isSubject ? "subject" : "", labelAll || (node.inCase && node.type !== "member") ? "labelled" : ""]
      .filter(Boolean)
      .join(" "),
  }));
  const links: cytoscape.ElementDefinition[] = edges.map((edge) => ({
    group: "edges",
    data: {
      id: edge.id,
      source: edge.source,
      target: edge.target,
      kind: edge.kind,
      count: edge.count,
      directed: edge.directed,
      inferred: edge.inferred,
      structural: edgeMeta(edge.kind).family !== "claim",
      hoverLabel: edgeHoverLabel(edge),
    },
  }));
  return [...nodes, ...links];
}

function runLayout(cy: cytoscape.Core, subjectId: string, layout: GraphLayout, hops: Map<string, number>): void {
  // Deterministic concentric seed by hop: subject centred, hop 1 inside, hop 2 and beyond outside.
  cy.layout({
    name: "concentric",
    animate: false,
    fit: true,
    padding: 32,
    avoidOverlap: true,
    minNodeSpacing: 40,
    startAngle: (3 / 2) * Math.PI,
    concentric: (node: cytoscape.NodeSingular) => 3 - Math.min(hops.get(node.id()) ?? 2, 2),
    levelWidth: () => 1,
    sort: (a: cytoscape.NodeSingular, b: cytoscape.NodeSingular) =>
      TYPE_ORDER.indexOf(String(a.data("type"))) - TYPE_ORDER.indexOf(String(b.data("type"))),
  } as cytoscape.LayoutOptions).run();
  if (layout === "rings") return;
  // fcose refines the seed without randomising, so the same input always gives the same picture.
  const options: FcoseLayoutOptions = {
    name: "fcose",
    quality: "proof",
    randomize: false,
    animate: false,
    fit: true,
    padding: 32,
    nodeDimensionsIncludeLabels: true,
    nodeRepulsion: () => 20000,
    nodeSeparation: 60,
    numIter: 2500,
    idealEdgeLength: (edge: cytoscape.EdgeSingular) => (edgeMeta(String(edge.data("kind"))).family === "shared" ? 90 : 120),
    fixedNodeConstraint: cy.getElementById(subjectId).nonempty() ? [{ nodeId: subjectId, position: { x: 0, y: 0 } }] : undefined,
  };
  cy.layout(options).run();
}

/** Dims everything outside the active node's 2-hop neighbourhood (§7.4). */
function focusHood(cy: cytoscape.Core, id: string): void {
  cy.batch(() => {
    cy.elements().removeClass("dimmed hop1");
    const node = cy.getElementById(id);
    if (node.empty()) return;
    const hop1 = node.closedNeighborhood();
    const hop2 = hop1.closedNeighborhood();
    cy.elements().not(hop2).addClass("dimmed");
    node.connectedEdges().addClass("hop1");
  });
}

function focusEdge(cy: cytoscape.Core, key: string): void {
  cy.batch(() => {
    cy.elements().removeClass("dimmed hop1");
    const edge = cy.getElementById(key);
    if (edge.empty()) return;
    const lit = edge.union(edge.connectedNodes()).closedNeighborhood();
    cy.elements().not(lit).addClass("dimmed");
    edge.addClass("hop1");
  });
}

/** The selection (or, with none, the case subject) drives the 2-hop highlight. */
function applySelection(cy: cytoscape.Core, subjectId: string, selection: GraphSelection | null): void {
  cy.elements().removeClass("picked");
  if (selection?.kind === "edge") {
    cy.getElementById(selection.key).addClass("picked");
    focusEdge(cy, selection.key);
    return;
  }
  const id = selection?.id ?? subjectId;
  if (selection) cy.getElementById(id).addClass("picked");
  focusHood(cy, id);
}

export interface GraphControls {
  zoomIn: () => void;
  zoomOut: () => void;
  fit: () => void;
  focusSubject: () => void;
}

interface CaseNetworkGraphProps {
  model: GraphModel;
  edges: GraphEdge[];
  hops: Map<string, number>;
  layout: GraphLayout;
  selection: GraphSelection | null;
  onSelect: (selection: GraphSelection | null) => void;
  /** Receives the zoom/fit commands once the graph is ready. */
  onReady: (controls: GraphControls) => void;
}

/** Cytoscape canvas for the case neighbourhood. Loaded lazily by NetworkPanel. */
export default function CaseNetworkGraph({ model, edges, hops, layout, selection, onSelect, onReady }: CaseNetworkGraphProps) {
  const hostRef = useRef<HTMLDivElement>(null);
  const cyRef = useRef<cytoscape.Core | null>(null);
  const onSelectRef = useRef(onSelect);
  const selectionRef = useRef(selection);
  useLayoutEffect(() => {
    onSelectRef.current = onSelect;
    selectionRef.current = selection;
  });

  useEffect(() => {
    const host = hostRef.current;
    if (!host) return;
    const cy = cytoscape({
      container: host,
      style: graphStyles(),
      minZoom: 0.4,
      maxZoom: 2.5,
      boxSelectionEnabled: false,
      autounselectify: true,
    });
    cyRef.current = cy;
    cy.on("tap", "node", (event) => onSelectRef.current({ kind: "node", id: event.target.id() }));
    cy.on("tap", "edge", (event) => {
      const edge = event.target as cytoscape.EdgeSingular;
      onSelectRef.current({
        kind: "edge",
        key: edge.id(),
        source: edge.source().id(),
        target: edge.target().id(),
        edgeKind: String(edge.data("kind")),
        directed: edge.data("directed") === true,
      });
    });
    cy.on("tap", (event) => {
      if (event.target === cy) onSelectRef.current(null);
    });
    cy.on("mouseover", "node", (event) => {
      host.style.cursor = "pointer";
      event.target.addClass("hovered");
      focusHood(cy, event.target.id());
    });
    cy.on("mouseout", "node", (event) => {
      host.style.cursor = "";
      event.target.removeClass("hovered");
      applySelection(cy, String(cy.scratch("subjectId")), selectionRef.current);
    });
    cy.on("mouseover", "edge", (event) => {
      host.style.cursor = "pointer";
      event.target.addClass("hovered");
    });
    cy.on("mouseout", "edge", (event) => {
      host.style.cursor = "";
      event.target.removeClass("hovered");
    });
    const resize = new ResizeObserver(() => cy.resize());
    resize.observe(host);
    return () => {
      resize.disconnect();
      cy.destroy();
      cyRef.current = null;
    };
  }, []);

  useEffect(() => {
    const cy = cyRef.current;
    if (!cy) return;
    let cancelled = false;
    const subjectId = model.subjectId;
    // The canvas only paints fonts that are already loaded.
    void document.fonts.load('500 11px "Inter Variable"').finally(() => {
      if (cancelled || cy.destroyed()) return;
      cy.scratch("subjectId", subjectId);
      cy.batch(() => {
        cy.elements().remove();
        cy.add(toElements(model, edges));
      });
      runLayout(cy, subjectId, layout, hops);
      applySelection(cy, subjectId, selectionRef.current);
      const zoomBy = (factor: number) =>
        cy.zoom({ level: cy.zoom() * factor, renderedPosition: { x: cy.width() / 2, y: cy.height() / 2 } });
      onReady({
        zoomIn: () => zoomBy(1.25),
        zoomOut: () => zoomBy(0.8),
        fit: () => cy.fit(undefined, 32),
        focusSubject: () => cy.fit(cy.getElementById(subjectId).closedNeighborhood(), 48),
      });
    });
    return () => {
      cancelled = true;
    };
  }, [model, edges, hops, layout, onReady]);

  useEffect(() => {
    const cy = cyRef.current;
    if (cy && cy.elements().nonempty()) applySelection(cy, model.subjectId, selection);
  }, [selection, model.subjectId]);

  return <div ref={hostRef} className="graph-canvas" />;
}
