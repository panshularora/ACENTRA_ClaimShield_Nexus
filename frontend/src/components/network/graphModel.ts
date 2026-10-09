import type {
  CaseAlert,
  ClaimRow,
  EdgeEvidence,
  NetworkEdge,
  NetworkNode,
  NetworkPack,
} from "../../api/types";
import { riskLevel, riskLevelFromConfirm, type RiskLevel } from "../../lib/risk";

/**
 * One adapter for both network shapes: today's /cases/{id}/network (untyped cliques, no
 * per-node case data) and the newer payload being added on fix/backend-p0 (in_case, is_subject,
 * alert_ids, flagged dollars, typed edges with direction, count and evidence ids, address hubs).
 * Fields the API does not send yet are derived from the case's own alerts and claim lines.
 */

export interface GraphNode {
  id: string;
  /** Normalised type: provider, owner, facility, member, address, phone or bank. */
  type: string;
  label: string;
  /** Label truncated to 22 characters for the canvas. */
  short: string;
  isSubject: boolean;
  /** Belongs to the case (subject, case providers, or touched by a flagged line). */
  inCase: boolean;
  masked: boolean;
  specialty?: string;
  /** Risk level for the ring; only where the API supports one (today: the subject's severity). */
  riskLevel?: RiskLevel;
  /** Patient-harm level where known (today: the subject's case harm); flagged at 3 and above. */
  harm: number | null;
  alertIds: string[];
  /** Null when no flagged line on this case touches the entity. */
  flaggedPaid: number | null;
  flaggedLines: number | null;
  /** Hop distance from the API, when sent. */
  hop?: number;
}

export interface GraphEdge {
  id: string;
  source: string;
  target: string;
  kind: string;
  directed: boolean;
  /** Underlying records merged into this edge. */
  count: number;
  evidenceIds: string[];
  inferred: boolean;
  inCase: boolean;
  label?: string;
  evidence?: EdgeEvidence;
}

export interface GraphModel {
  subjectId: string;
  nodes: GraphNode[];
  edges: GraphEdge[];
}

export interface GraphContext {
  /** case.entity_ids: providers grouped into the case. */
  caseEntityIds?: string[];
  alerts?: CaseAlert[];
  rows?: ClaimRow[];
  subjectSeverity?: number;
  subjectHarm?: number;
}

const TYPE_ALIASES: Record<string, string> = {
  location: "address",
  service_location: "address",
  contact: "phone",
  contact_point: "phone",
  tin: "bank",
  bank_account: "bank",
};

/** Edge kinds whose direction is meaningful. */
const DIRECTED_KINDS = new Set([
  "owns",
  "referral",
  "billed",
  "rendered",
  "at_facility",
  "located_at",
  "prescribed",
  "dispensed",
]);

const MAX_LABEL = 22;

function shorten(label: string): string {
  return label.length > MAX_LABEL ? `${label.slice(0, MAX_LABEL - 1)}…` : label;
}

function peerIds(alert: CaseAlert): string[] {
  const ids = alert.evidence.peer_ids;
  return Array.isArray(ids) ? ids.filter((id): id is string => typeof id === "string") : [];
}

function rowEntityIds(row: ClaimRow): string[] {
  return [row.rendering_provider_id, row.billing_provider_id, row.facility_id, row.member.member_id].filter(
    (id): id is string => Boolean(id),
  );
}

interface LineTotals {
  paid: number;
  lines: number;
}

function lineTotals(rows: ClaimRow[]): Map<string, LineTotals> {
  const totals = new Map<string, LineTotals>();
  for (const row of rows) {
    for (const id of new Set(rowEntityIds(row))) {
      const hit = totals.get(id) ?? { paid: 0, lines: 0 };
      hit.paid += row.paid;
      hit.lines += 1;
      totals.set(id, hit);
    }
  }
  return totals;
}

function normaliseNode(node: NetworkNode, subjectId: string, ctx: GraphContext, totals: Map<string, LineTotals>): GraphNode {
  const isSubject = node.is_subject ?? (node.primary === true || node.id === subjectId);
  const derivedAlerts = (ctx.alerts ?? [])
    .filter((alert) => alert.entity_id === node.id || peerIds(alert).includes(node.id))
    .map((alert) => alert.alert_id);
  const total = totals.get(node.id);
  const flaggedPaid = node.flagged_paid ?? total?.paid ?? null;
  const flaggedLines = node.n_flagged_lines ?? total?.lines ?? null;
  const inCase =
    node.in_case ??
    (isSubject || (ctx.caseEntityIds ?? []).includes(node.id) || (node.type !== "member" && total !== undefined));
  const harmLevel = node.harm ?? (isSubject ? ctx.subjectHarm : undefined);
  const severity = node.severity ?? (isSubject ? ctx.subjectSeverity : undefined);
  const ring =
    severity !== undefined
      ? riskLevel(severity)
      : node.risk !== undefined
        ? riskLevelFromConfirm(node.risk)
        : undefined;
  return {
    id: node.id,
    type: TYPE_ALIASES[node.type] ?? node.type,
    label: node.label,
    short: shorten(node.label),
    isSubject,
    inCase,
    masked: node.masked === true,
    specialty: node.specialty,
    riskLevel: ring,
    harm: harmLevel ?? null,
    alertIds: node.alert_ids ?? derivedAlerts,
    flaggedPaid,
    flaggedLines,
    hop: node.hop,
  };
}

/** Merges duplicate and reverse-duplicate edges; keeps direction where it means something. */
function normaliseEdges(edges: NetworkEdge[], known: Set<string>): GraphEdge[] {
  const merged = new Map<string, GraphEdge>();
  for (const edge of edges) {
    if (!known.has(edge.source) || !known.has(edge.target)) continue;
    const reversed = edge.direction === "in";
    const source = reversed ? edge.target : edge.source;
    const target = reversed ? edge.source : edge.target;
    const directed = edge.direction ? edge.direction !== "none" : DIRECTED_KINDS.has(edge.kind);
    const [a, b] = directed ? [source, target] : [source, target].sort();
    const id = edge.id ?? `${edge.kind}:${a}${directed ? "->" : "--"}${b}`;
    const key = edge.id ?? id;
    const hit = merged.get(key);
    const evidence = edge.evidence_ids ?? [];
    if (hit) {
      hit.count += edge.count ?? 1;
      hit.evidenceIds = [...new Set([...hit.evidenceIds, ...evidence])];
    } else {
      merged.set(key, {
        id,
        source: a,
        target: b,
        kind: edge.kind,
        directed,
        count: edge.count ?? 1,
        evidenceIds: evidence,
        inferred: edge.inferred === true,
        inCase: edge.in_case === true,
        label: edge.label,
        evidence: edge.evidence,
      });
    }
  }
  return [...merged.values()];
}

/** Normalises either network shape into the model the graph, legend and lists render. */
export function normalizeNetwork(pack: NetworkPack, ctx: GraphContext = {}): GraphModel {
  const totals = lineTotals(ctx.rows ?? []);
  const nodes = pack.nodes.map((node) => normaliseNode(node, pack.primary_entity_id, ctx, totals));
  const subject = nodes.find((node) => node.isSubject);
  return {
    subjectId: subject?.id ?? pack.primary_entity_id,
    nodes,
    edges: normaliseEdges(pack.edges, new Set(nodes.map((node) => node.id))),
  };
}
