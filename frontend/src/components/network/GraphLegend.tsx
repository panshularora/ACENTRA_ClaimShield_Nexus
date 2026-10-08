import { RISK_GLYPH, RISK_LABEL, RISK_LEVELS } from "../../lib/risk";
import type { GraphEdge, GraphNode } from "./graphModel";
import { EDGE_FAMILY_COLOR, NODE_TYPES, edgeKindCounts, edgeMeta, type EdgeFamily } from "./networkModel";

interface EdgeKindFilterProps {
  edges: GraphEdge[];
  enabled: Record<string, boolean>;
  onToggle: (kind: string, on: boolean) => void;
}

/** Edge-kind checkboxes styled as chips, above the graph (design system §7.8). */
export function EdgeKindFilter({ edges, enabled, onToggle }: EdgeKindFilterProps) {
  return (
    <fieldset className="chip-filter">
      <legend>Show links</legend>
      {edgeKindCounts(edges).map(({ kind, count }) => {
        const meta = edgeMeta(kind);
        return (
          <label key={kind} className="chip" title={meta.meaning}>
            <input type="checkbox" checked={enabled[kind] !== false} onChange={(event) => onToggle(kind, event.target.checked)} />
            <span>{meta.label}</span>
            <span className="chip-count">{count}</span>
          </label>
        );
      })}
    </fieldset>
  );
}

const FAMILY_SAMPLES: { family: EdgeFamily; label: string; arrow: boolean; width: number }[] = [
  { family: "claim", label: "Billed / rendered", arrow: false, width: 1 },
  { family: "shared", label: "Shared address / TIN / contact", arrow: false, width: 1.5 },
  { family: "ownership", label: "Owns", arrow: true, width: 2 },
  { family: "referral", label: "Referral", arrow: true, width: 2 },
];

function EdgeSample({ family, arrow, width, dashed }: { family: EdgeFamily; arrow: boolean; width: number; dashed?: boolean }) {
  const color = `var(${EDGE_FAMILY_COLOR[family]})`;
  return (
    <svg width="24" height="10" viewBox="0 0 24 10" aria-hidden="true" focusable="false">
      <line x1="1" y1="5" x2={arrow ? 18 : 23} y2="5" stroke={color} strokeWidth={width} strokeDasharray={dashed ? "4 3" : undefined} />
      {arrow ? <path d="M17 1.5 L23 5 L17 8.5 Z" fill={color} /> : null}
    </svg>
  );
}

interface GraphLegendProps {
  nodes: GraphNode[];
  edges: GraphEdge[];
}

/** Caption legend under the canvas listing only the types and encodings present (design system §7.8). */
export function GraphLegend({ nodes, edges }: GraphLegendProps) {
  const types = Object.keys(NODE_TYPES).filter((type) => nodes.some((node) => node.type === type));
  const families = FAMILY_SAMPLES.filter(({ family }) => edges.some((edge) => edgeMeta(edge.kind).family === family));
  const inferred = edges.some((edge) => edge.inferred);
  const hasRisk = nodes.some((node) => node.riskLevel);
  const hasHarm = nodes.some((node) => (node.harm ?? 0) >= 3);
  const hasCase = nodes.some((node) => node.inCase && !node.isSubject && node.type !== "member");

  return (
    <div className="graph-legend">
      <ul aria-label="Entity types">
        <li>
          <span className="legend-shape is-subject" aria-hidden="true" />
          Case subject
        </li>
        {hasCase ? (
          <li>
            <span className="legend-shape shape-circle is-case" aria-hidden="true" />
            In this case (heavy outline)
          </li>
        ) : null}
        {types.map((type) => (
          <li key={type}>
            <span className={`legend-shape shape-${NODE_TYPES[type].shape} type-${type}`} aria-hidden="true" />
            {NODE_TYPES[type].label}
          </li>
        ))}
      </ul>
      <ul aria-label="Link types">
        {families.map((sample) => (
          <li key={sample.family}>
            <EdgeSample {...sample} />
            {sample.label}
          </li>
        ))}
        {inferred ? (
          <li>
            <EdgeSample family="shared" arrow={false} width={1} dashed />
            Inferred
          </li>
        ) : null}
      </ul>
      {hasRisk || hasHarm ? (
        <ul aria-label="Encodings">
          {hasRisk ? (
            <>
              <li>Ring = risk level</li>
              {RISK_LEVELS.map((level) => (
                <li key={level}>
                  <span className={`legend-ring risk-${level}`} aria-hidden="true" />
                  {RISK_GLYPH[level]} {RISK_LABEL[level]}
                </li>
              ))}
            </>
          ) : null}
          {hasHarm ? (
            <li>
              <span className="legend-harm" aria-hidden="true" />
              Dot = patient harm
            </li>
          ) : null}
        </ul>
      ) : null}
    </div>
  );
}
