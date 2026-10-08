import type { EdgeSingular, NodeSingular, StylesheetJson } from "cytoscape";
import { RISK_LEVELS } from "../../lib/risk";
import { token } from "../../lib/theme";
import { EDGE_FAMILY_COLOR, EDGE_TYPES, edgeWidth } from "./networkModel";

const uri = (svg: string) => `data:image/svg+xml;utf8,${encodeURIComponent(svg)}`;
const EMPTY = uri('<svg xmlns="http://www.w3.org/2000/svg" width="1" height="1"/>');

const NODE_SHAPES: [type: string, shape: string, width: number, height: number][] = [
  ["provider", "ellipse", 28, 28],
  ["owner", "round-rectangle", 24, 24],
  ["facility", "round-rectangle", 30, 22],
  ["address", "diamond", 24, 24],
  ["phone", "ellipse", 14, 14],
  ["bank", "hexagon", 24, 24],
  ["member", "triangle", 16, 16],
];

const edgeWidthOf = (edge: EdgeSingular) =>
  edgeWidth({ kind: String(edge.data("kind")), count: Number(edge.data("count") ?? 1), inferred: edge.data("inferred") === true });

/** Cytoscape stylesheet from design system §7.7, with tokens resolved to concrete colours for the canvas. */
export function graphStyles(): StylesheetJson {
  const harmDot = uri(
    `<svg xmlns="http://www.w3.org/2000/svg" width="12" height="12"><circle cx="6" cy="6" r="4.5" fill="${token("--harm-solid")}" stroke="${token("--graph-bg")}" stroke-width="1.5"/></svg>`,
  );
  const fade = token("--duration-fast");
  const kindsOf = (family: string) =>
    Object.entries(EDGE_TYPES)
      .filter(([, meta]) => meta.family === family)
      .map(([kind]) => `edge[kind = "${kind}"]`)
      .join(", ");

  return [
    { selector: "core", style: { "active-bg-opacity": 0, "selection-box-opacity": 0 } },
    {
      selector: "node",
      style: {
        shape: "ellipse",
        width: 28,
        height: 28,
        "background-color": token("--graph-node-provider-fill"),
        "border-color": token("--graph-node-provider-stroke"),
        "border-width": Number.parseFloat(token("--graph-node-stroke-width")) || 1.5,
        // layer 0 = type glyph, layer 1 = harm notch
        "background-image": (node: NodeSingular) => [node.data("icon") ?? EMPTY, node.data("harm") ? harmDot : EMPTY],
        "background-width": ["50%", "12px"],
        "background-height": ["50%", "12px"],
        "background-position-x": ["50%", "100%"],
        "background-position-y": ["50%", "0%"],
        "background-clip": ["node", "none"],
        "background-image-containment": ["inside", "over"],
        "bounds-expansion": 8,
        label: "",
        color: token("--color-text"),
        "font-family": token("--font-sans"),
        "font-size": 11,
        "font-weight": 500,
        "text-valign": "bottom",
        "text-margin-y": 6,
        "text-outline-color": token("--graph-label-halo"),
        "text-outline-width": 3,
        "min-zoomed-font-size": 8,
        "overlay-opacity": 0,
        "transition-property": "opacity",
        "transition-duration": fade,
      },
    },
    ...NODE_SHAPES.map(([type, shape, width, height]) => ({
      selector: `node[type = "${type}"]`,
      style: {
        shape,
        width,
        height,
        "background-color": token(`--graph-node-${type}-fill`),
        "border-color": token(`--graph-node-${type}-stroke`),
      },
    })),
    // Case entities (the case's own providers) get a heavier ink border so they read apart from context.
    { selector: "node[?inCase]", style: { "border-width": 2.5, "border-color": token("--color-text") } },
    { selector: "node.hovered", style: { "border-width": 2.5 } },
    ...RISK_LEVELS.map((level) => ({
      selector: `node[risk = "${level}"]`,
      style: { "outline-width": 2.5, "outline-offset": 2, "outline-color": token(`--risk-${level}-solid`) },
    })),
    {
      selector: "node.subject",
      style: {
        width: 44,
        height: 44,
        "background-color": token("--graph-subject-fill"),
        "border-width": 0,
        "outline-width": 3,
        "outline-offset": 2,
        "outline-color": token("--graph-subject-ring-fallback"),
        label: "data(short)",
        "font-size": 12,
        "font-weight": 600,
      },
    },
    ...RISK_LEVELS.map((level) => ({
      selector: `node.subject[risk = "${level}"]`,
      style: { "outline-color": token(`--risk-${level}-solid`) },
    })),
    { selector: "node.labelled, node.hovered, node.picked", style: { label: "data(short)" } },
    {
      selector: "node.picked",
      style: { "outline-width": 2, "outline-offset": 2, "outline-color": token("--color-focus") },
    },
    ...RISK_LEVELS.map((level) => ({
      selector: `node[risk = "${level}"].picked`,
      style: { "border-width": 2.5, "border-color": token(`--risk-${level}-solid`) },
    })),
    {
      selector: "edge",
      style: {
        width: edgeWidthOf,
        "line-color": token(EDGE_FAMILY_COLOR.claim),
        "target-arrow-color": token(EDGE_FAMILY_COLOR.claim),
        "curve-style": "bezier",
        "line-cap": "round",
        "target-arrow-shape": "none",
        "arrow-scale": 0.8,
        "overlay-opacity": 0,
        label: "",
        "font-family": token("--font-sans"),
        "font-size": 11,
        color: token("--color-text-muted"),
        "text-background-color": token("--graph-label-halo"),
        "text-background-opacity": 1,
        "text-background-padding": "2px",
        "text-rotation": "autorotate",
        "min-zoomed-font-size": 8,
        "transition-property": "opacity",
        "transition-duration": fade,
      },
    },
    {
      selector: kindsOf("shared"),
      style: { "line-color": token(EDGE_FAMILY_COLOR.shared), "target-arrow-color": token(EDGE_FAMILY_COLOR.shared) },
    },
    {
      selector: kindsOf("ownership"),
      style: { "line-color": token(EDGE_FAMILY_COLOR.ownership), "target-arrow-color": token(EDGE_FAMILY_COLOR.ownership) },
    },
    {
      selector: kindsOf("referral"),
      style: { "line-color": token(EDGE_FAMILY_COLOR.referral), "target-arrow-color": token(EDGE_FAMILY_COLOR.referral) },
    },
    { selector: "edge[?directed]", style: { "target-arrow-shape": "triangle" } },
    { selector: "edge[?inferred]", style: { "line-style": "dashed", "line-dash-pattern": [4, 3] } },
    { selector: "edge.hop1", style: { width: (edge: EdgeSingular) => edgeWidthOf(edge) + 0.75 } },
    { selector: "edge.hovered, edge.picked", style: { label: "data(hoverLabel)" } },
    { selector: "edge.picked", style: { "line-color": token("--color-focus"), "target-arrow-color": token("--color-focus") } },
    { selector: ".dimmed", style: { opacity: Number(token("--graph-dim-opacity")) || 0.15 } },
  ] as StylesheetJson;
}
