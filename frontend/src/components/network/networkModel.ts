import { humanize } from "../../lib/format";
import type { TokenName } from "../../lib/theme";
import type { GraphEdge, GraphModel, GraphNode } from "./graphModel";

/** Edge families from design system §7.2: colour by family, all solid; dashes only for inferred links. */
export type EdgeFamily = "claim" | "shared" | "ownership" | "referral";

export const EDGE_FAMILY_COLOR: Record<EdgeFamily, TokenName> = {
  claim: "--graph-edge-claim",
  shared: "--graph-edge-shared",
  ownership: "--graph-edge-ownership",
  referral: "--graph-edge-referral",
};

export interface EdgeTypeMeta {
  label: string;
  /** Plain-language meaning, shown in the legend and the selection card. */
  meaning: string;
  family: EdgeFamily;
}

/** Edge kinds sent today plus the ones the newer network payload adds (shared_contact, shared_owner). */
export const EDGE_TYPES: Record<string, EdgeTypeMeta> = {
  shared_tin: { label: "Shared TIN", meaning: "Both providers bill under the same tax ID.", family: "shared" },
  shared_location: {
    label: "Shared address",
    meaning: "Both providers are enrolled at the same service location.",
    family: "shared",
  },
  shared_contact: { label: "Shared phone/contact", meaning: "Both providers list the same phone or contact point.", family: "shared" },
  owns: { label: "Owns", meaning: "Ownership link from the enrolment record (owner → provider).", family: "ownership" },
  shared_owner: { label: "Same owner", meaning: "Both providers have the same owner on record.", family: "ownership" },
  referral: { label: "Referral", meaning: "Referrals from one provider to the other (referrer → receiver).", family: "referral" },
  billed: { label: "Billed", meaning: "Billing provider on a flagged claim for this member.", family: "claim" },
  rendered: { label: "Rendered", meaning: "Rendering provider on a flagged claim line for this member.", family: "claim" },
  at_facility: { label: "At facility", meaning: "Flagged line was rendered at this facility.", family: "claim" },
  located_at: { label: "Practice address", meaning: "Provider enrolled at this address hub.", family: "shared" },
  prescribed: { label: "Prescribed", meaning: "Prescriber wrote a fill for this member.", family: "claim" },
  dispensed: { label: "Dispensed", meaning: "Pharmacy dispensed a fill for this member.", family: "claim" },
};

export function edgeMeta(kind: string): EdgeTypeMeta {
  return (
    EDGE_TYPES[kind] ?? {
      label: humanize(kind),
      meaning: "Relationship type sent by the API without a UI description.",
      family: kind.startsWith("shared") ? "shared" : "claim",
    }
  );
}

/** Edge width from design system §7.2: claim and referral scale with count (1–3px). */
export function edgeWidth(edge: Pick<GraphEdge, "kind" | "count" | "inferred">): number {
  if (edge.inferred) return 1;
  const family = edgeMeta(edge.kind).family;
  if (family === "ownership") return 2;
  if (family === "shared") return 1.5;
  return 1 + 2 * Math.min(1, Math.max(0, (edge.count - 1) / 4));
}

export function edgeHoverLabel(edge: GraphEdge): string {
  const label = edgeMeta(edge.kind).label;
  return edge.count > 1 ? `${label} · ${edge.count} records` : label;
}

export interface NodeTypeMeta {
  label: string;
  plural: string;
  /** Legend glyph for the mini-shape. */
  shape: "circle" | "square" | "rect" | "diamond" | "hexagon" | "triangle" | "dot";
}

/** Node types from design system §7.1: shape + glyph + quiet tint. Address/phone/bank arrive with the newer API. */
export const NODE_TYPES: Record<string, NodeTypeMeta> = {
  provider: { label: "Provider", plural: "Providers", shape: "circle" },
  owner: { label: "Owner", plural: "Owners", shape: "square" },
  facility: { label: "Facility", plural: "Facilities", shape: "rect" },
  address: { label: "Address", plural: "Addresses", shape: "diamond" },
  bank: { label: "Bank / TIN", plural: "Banks / TINs", shape: "hexagon" },
  phone: { label: "Phone", plural: "Phones", shape: "dot" },
  member: { label: "Member", plural: "Members", shape: "triangle" },
};

export function nodeMeta(type: string): NodeTypeMeta {
  return NODE_TYPES[type] ?? { label: humanize(type), plural: humanize(type), shape: "circle" };
}

/** Undirected hop distance from the case subject over the given edges. */
export function hopDistances(model: GraphModel, edges: GraphEdge[] = model.edges): Map<string, number> {
  const adjacency = new Map<string, string[]>();
  for (const edge of edges) {
    adjacency.set(edge.source, [...(adjacency.get(edge.source) ?? []), edge.target]);
    adjacency.set(edge.target, [...(adjacency.get(edge.target) ?? []), edge.source]);
  }
  const dist = new Map<string, number>([[model.subjectId, 0]]);
  const queue = [model.subjectId];
  while (queue.length > 0) {
    const current = queue.shift()!;
    const next = (dist.get(current) ?? 0) + 1;
    for (const neighbour of adjacency.get(current) ?? []) {
      if (!dist.has(neighbour)) {
        dist.set(neighbour, next);
        queue.push(neighbour);
      }
    }
  }
  return dist;
}

export interface Relation {
  kind: string;
  /** The node at the other end of the edge. */
  other: GraphNode;
  direction: "out" | "in" | "none";
  count: number;
}

export interface LinkedEntity {
  node: GraphNode;
  /** Hops from the subject; null when not connected by enabled edges. */
  hop: number | null;
  relations: Relation[];
}

const TYPE_ORDER = Object.keys(NODE_TYPES);

/** Per-node relationship summary used by the keyboard-accessible list and the selection card. */
export function linkedEntities(model: GraphModel, edges: GraphEdge[]): LinkedEntity[] {
  const nodes = new Map(model.nodes.map((n) => [n.id, n]));
  const hops = hopDistances(model, edges);
  const relations = new Map<string, Relation[]>();
  const push = (id: string, relation: Relation) => relations.set(id, [...(relations.get(id) ?? []), relation]);
  for (const edge of edges) {
    const source = nodes.get(edge.source);
    const target = nodes.get(edge.target);
    if (!source || !target) continue;
    push(source.id, { kind: edge.kind, other: target, direction: edge.directed ? "out" : "none", count: edge.count });
    push(target.id, { kind: edge.kind, other: source, direction: edge.directed ? "in" : "none", count: edge.count });
  }
  return model.nodes
    .map((node) => ({ node, hop: hops.get(node.id) ?? null, relations: relations.get(node.id) ?? [] }))
    .sort(
      (a, b) =>
        (a.hop ?? 99) - (b.hop ?? 99) ||
        Number(b.node.inCase) - Number(a.node.inCase) ||
        TYPE_ORDER.indexOf(a.node.type) - TYPE_ORDER.indexOf(b.node.type) ||
        a.node.label.localeCompare(b.node.label),
    );
}

/** Counts per edge kind, in legend order (known kinds first). */
export function edgeKindCounts(edges: GraphEdge[]): { kind: string; count: number }[] {
  const counts = new Map<string, number>();
  for (const edge of edges) counts.set(edge.kind, (counts.get(edge.kind) ?? 0) + 1);
  const known = Object.keys(EDGE_TYPES).filter((kind) => counts.has(kind));
  const extra = [...counts.keys()].filter((kind) => !(kind in EDGE_TYPES)).sort();
  return [...known, ...extra].map((kind) => ({ kind, count: counts.get(kind) ?? 0 }));
}

/** "organic" = concentric seed refined by fcose; "rings" = the concentric seed alone (hop distance). */
export type GraphLayout = "organic" | "rings";

export type GraphSelection =
  | { kind: "node"; id: string }
  | { kind: "edge"; key: string; source: string; target: string; edgeKind: string; directed: boolean };

/** One-sentence summary of the network for screen readers. */
export function networkSummary(model: GraphModel, edges: GraphEdge[]): string {
  const byType = new Map<string, number>();
  for (const node of model.nodes) byType.set(node.type, (byType.get(node.type) ?? 0) + 1);
  const nodes = [...byType.entries()].map(
    ([type, n]) => `${n} ${(n === 1 ? nodeMeta(type).label : nodeMeta(type).plural).toLowerCase()}`,
  );
  const kinds = edgeKindCounts(edges).map(({ kind, count }) => `${count} ${edgeMeta(kind).label.toLowerCase()}`);
  const inCase = model.nodes.filter((n) => n.inCase && n.type !== "member").length;
  return `${model.nodes.length} entities (${nodes.join(", ")}), ${inCase} in this case, joined by ${edges.length} links (${kinds.join(", ")}).`;
}
