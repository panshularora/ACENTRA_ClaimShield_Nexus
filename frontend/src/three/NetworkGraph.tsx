import { useMemo, useState } from "react";
import type { NetworkEdge, NetworkNode, NetworkPack } from "../api/types";

const TYPE_COLOR: Record<string, string> = {
  provider: "#1aa24c",
  member: "#c49a3c",
  facility: "#3d7ea6",
  owner: "#b94832",
};

function hash01(value: string): number {
  let h = 2166136261;
  for (let i = 0; i < value.length; i += 1) {
    h = Math.imul(h ^ value.charCodeAt(i), 16777619);
  }
  return (h >>> 0) / 4294967296;
}

function layout(nodes: NetworkNode[], width: number, height: number): Record<string, { x: number; y: number }> {
  const cx = width / 2;
  const cy = height / 2 + 8;
  const groups: Record<string, NetworkNode[]> = {};
  for (const node of nodes) {
    (groups[node.type] ??= []).push(node);
  }
  const pos: Record<string, { x: number; y: number }> = {};
  const placeArc = (
    list: NetworkNode[],
    radius: number,
    start: number,
    sweep: number,
    yScale = 0.78,
  ) => {
    list.forEach((node, index) => {
      const t = list.length === 1 ? 0.5 : index / (list.length - 1);
      const angle = start + t * sweep;
      pos[node.id] = {
        x: cx + Math.cos(angle) * radius,
        y: cy + Math.sin(angle) * radius * yScale,
      };
    });
  };

  const primary = nodes.find((n) => n.primary);
  if (primary) pos[primary.id] = { x: cx + 36, y: cy };

  const providers = (groups.provider ?? []).filter((n) => !n.primary);
  placeArc(providers, 128, -Math.PI * 0.95, Math.PI * 1.85, 0.86);

  placeArc(groups.facility ?? [], 196, -Math.PI * 0.25, Math.PI * 0.7, 0.78);
  placeArc(groups.owner ?? [], 88, -Math.PI * 1.2, Math.PI * 0.45, 0.8);

  const members = groups.member ?? [];
  if (members.length === 1 && members[0].id === "__members__") {
    pos[members[0].id] = { x: 78, y: cy + 10 };
  } else {
    members.forEach((node) => {
      const a = hash01(node.id) * Math.PI * 1.6 + Math.PI * 0.7;
      const r = 118 + hash01(node.id + "r") * 86;
      pos[node.id] = {
        x: cx + Math.cos(a) * r * 1.05,
        y: cy + Math.sin(a) * r * 0.62,
      };
    });
  }

  for (const node of nodes) {
    if (!pos[node.id]) pos[node.id] = { x: cx, y: cy };
  }
  return pos;
}

function clip(label: string, n = 22): string {
  return label.length > n ? `${label.slice(0, n - 1)}…` : label;
}

function nodeSize(node: NetworkNode): number {
  if (node.id === "__members__") return 14;
  if (node.primary) return 11;
  if (node.type === "provider") return 8;
  if (node.type === "facility") return 7;
  return 5.5;
}

function compactPack(pack: NetworkPack): NetworkPack {
  const members = pack.nodes.filter((node) => node.type === "member");
  if (members.length <= 8) return pack;
  const keepIds = new Set(pack.nodes.filter((node) => node.type !== "member").map((n) => n.id));
  const aggId = "__members__";
  const nodes: NetworkNode[] = [
    ...pack.nodes.filter((node) => node.type !== "member"),
    {
      id: aggId,
      type: "member",
      label: `${members.length} members`,
      primary: false,
    },
  ];
  const seen = new Set<string>();
  const edges: NetworkEdge[] = [];
  for (const edge of pack.edges) {
    const source = keepIds.has(edge.source) ? edge.source : aggId;
    const target = keepIds.has(edge.target) ? edge.target : aggId;
    if (source === target) continue;
    const key = `${source}|${target}|${edge.kind}`;
    if (seen.has(key)) continue;
    seen.add(key);
    edges.push({ ...edge, source, target });
  }
  return { ...pack, nodes, edges };
}

export function NetworkGraph({
  pack,
  enabled,
  onSelect,
}: {
  pack: NetworkPack;
  enabled: Record<string, boolean>;
  onSelect: (id: string, type: string) => void;
  reduced?: boolean;
}) {
  const view = useMemo(() => compactPack(pack), [pack]);
  const [picked, setPicked] = useState<string | null>(pack.primary_entity_id);
  const [hover, setHover] = useState<string | null>(null);
  const width = 560;
  const height = 420;
  const positions = useMemo(() => layout(view.nodes, width, height), [view.nodes]);
  const edges = useMemo(
    () => view.edges.filter((edge) => enabled[edge.kind] !== false),
    [view.edges, enabled],
  );
  const active = hover ?? picked;

  return (
    <svg
      className="net-map"
      viewBox={`0 0 ${width} ${height}`}
      role="img"
      aria-label="Static two-hop relationship map"
    >
      <rect width={width} height={height} fill="#f7fbf8" rx="12" />
      {edges.map((edge, i) => (
        <EdgePath key={`${edge.source}-${edge.target}-${edge.kind}-${i}`} edge={edge} positions={positions} />
      ))}
      {view.nodes.map((node) => {
        const p = positions[node.id];
        if (!p) return null;
        const r = nodeSize(node);
        const color = TYPE_COLOR[node.type] ?? "#3d5a63";
        const isActive = active === node.id || node.primary;
        return (
          <g
            key={node.id}
            className="net-node"
            transform={`translate(${p.x}, ${p.y})`}
            onClick={(event) => {
              event.stopPropagation();
              setPicked(node.id);
              if (node.id !== "__members__") onSelect(node.id, node.type);
            }}
            onMouseEnter={() => setHover(node.id)}
            onMouseLeave={() => setHover(null)}
            role="button"
            tabIndex={0}
            onKeyDown={(event) => {
              if (event.key === "Enter" || event.key === " ") {
                event.preventDefault();
                setPicked(node.id);
                onSelect(node.id, node.type);
              }
            }}
          >
            {isActive && <circle r={r + 6} fill={color} opacity={0.16} />}
            <circle r={r} fill={color} stroke="#fff" strokeWidth={1.6} />
            {(isActive || node.primary || node.id === "__members__") && (
              <text y={r + 14} textAnchor="middle" className="net-label">
                {clip(node.label, node.type === "provider" ? 16 : 22)}
              </text>
            )}
          </g>
        );
      })}
    </svg>
  );
}

function EdgePath({
  edge,
  positions,
}: {
  edge: NetworkEdge;
  positions: Record<string, { x: number; y: number }>;
}) {
  const a = positions[edge.source];
  const b = positions[edge.target];
  if (!a || !b) return null;
  const hot = edge.kind === "referral" || edge.kind === "owns" || edge.kind.includes("shared");
  return (
    <line
      x1={a.x}
      y1={a.y}
      x2={b.x}
      y2={b.y}
      stroke={hot ? "#7bb98d" : "#c9d7ce"}
      strokeWidth={hot ? 1.6 : 1}
      strokeLinecap="round"
    />
  );
}
