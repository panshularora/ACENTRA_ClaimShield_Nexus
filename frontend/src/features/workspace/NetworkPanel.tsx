import cytoscape from "cytoscape";
import { useEffect, useMemo, useRef, useState } from "react";
import type { NetworkNode, NetworkPack } from "../../api/types";

const EDGE_KINDS = [
  "rendered",
  "billed",
  "at_facility",
  "owns",
  "referral",
  "shared_location",
  "shared_tin",
];

export function NetworkPanel({
  pack,
  loading,
  error,
  onSelect,
}: {
  pack: NetworkPack | undefined;
  loading: boolean;
  error: string | null;
  onSelect: (id: string, type: string) => void;
}) {
  const host = useRef<HTMLDivElement>(null);
  const cyRef = useRef<cytoscape.Core | null>(null);
  const [enabled, setEnabled] = useState<Record<string, boolean>>(() =>
    Object.fromEntries(EDGE_KINDS.map((k) => [k, true])),
  );
  const [picked, setPicked] = useState<NetworkNode | null>(null);

  const kindsPresent = useMemo(() => {
    const set = new Set((pack?.edges ?? []).map((e) => e.kind));
    return EDGE_KINDS.filter((k) => set.has(k));
  }, [pack]);

  useEffect(() => {
    if (!host.current || !pack) return;
    cyRef.current?.destroy();
    const visibleEdges = pack.edges.filter((e) => enabled[e.kind] !== false);
    const cy = cytoscape({
      container: host.current,
      elements: [
        ...pack.nodes.map((n) => ({ data: { ...n } })),
        ...visibleEdges.map((e, i) => ({
          data: { id: `e${i}-${e.source}-${e.target}-${e.kind}`, ...e },
        })),
      ],
      style: [
        {
          selector: "node",
          style: {
            label: "data(label)",
            "font-family": "IBM Plex Sans, sans-serif",
            "font-size": 8,
            "text-wrap": "ellipsis",
            "text-max-width": "72px",
            color: "#161c22",
            "background-color": "#d9dce8",
            "border-width": 1,
            "border-color": "#18232e",
            width: 18,
            height: 18,
          },
        },
        {
          selector: 'node[type = "provider"]',
          style: { "background-color": "#18232e", color: "#efe8d6", shape: "rectangle", width: 22, height: 16 },
        },
        {
          selector: 'node[type = "member"]',
          style: { "background-color": "#eadcc0", shape: "ellipse" },
        },
        {
          selector: 'node[type = "facility"]',
          style: { "background-color": "#d5e6df", shape: "diamond", width: 16, height: 16 },
        },
        {
          selector: 'node[type = "owner"]',
          style: { "background-color": "#3e5368", color: "#efe8d6", shape: "hexagon" },
        },
        {
          selector: "node[?primary]",
          style: { "border-width": 3, "border-color": "#9b2f24", width: 26, height: 20 },
        },
        {
          selector: "edge",
          style: {
            width: 1,
            "line-color": "#cfc6b2",
            "curve-style": "haystack",
            "haystack-radius": 0.4,
          },
        },
        {
          selector: 'edge[kind = "referral"]',
          style: { "line-color": "#1c5a4c", width: 1.6 },
        },
        {
          selector: 'edge[kind = "owns"]',
          style: { "line-color": "#3e5368", "line-style": "dashed" },
        },
        {
          selector: ":selected",
          style: { "border-color": "#0b3d8c", "line-color": "#0b3d8c" },
        },
      ],
      layout: { name: "cose", animate: false, padding: 12, nodeRepulsion: 6000 },
      userZoomingEnabled: true,
      userPanningEnabled: true,
      boxSelectionEnabled: false,
    });
    cy.on("tap", "node", (evt) => {
      const data = evt.target.data() as NetworkNode;
      setPicked(data);
      onSelect(data.id, data.type);
    });
    cyRef.current = cy;
    return () => {
      cy.destroy();
      cyRef.current = null;
    };
  }, [pack, enabled, onSelect]);

  return (
    <section className="ws-panel ws-network" aria-labelledby="net-title">
      <header className="ws-panel-head">
        <div>
          <p className="kicker">Panel 5</p>
          <h2 id="net-title">Network · 2-hop</h2>
        </div>
        {pack && (
          <span className="muted mono">
            {pack.nodes.length}n · {pack.edges.length}e
          </span>
        )}
      </header>
      {loading && <p className="muted">Loading neighbourhood…</p>}
      {error && <p className="error-text">{error}</p>}
      {!loading && pack && pack.nodes.length === 0 && <p className="empty">No graph neighbourhood.</p>}
      {kindsPresent.length > 0 && (
        <fieldset className="edge-filters">
          <legend>Edge types</legend>
          {kindsPresent.map((kind) => (
            <label key={kind}>
              <input
                type="checkbox"
                checked={enabled[kind] !== false}
                onChange={(e) => setEnabled((prev) => ({ ...prev, [kind]: e.target.checked }))}
              />
              {kind.replaceAll("_", " ")}
            </label>
          ))}
        </fieldset>
      )}
      <div className="cy-host" ref={host} role="img" aria-label="Case relationship graph" />
      {picked && (
        <p className="net-pick">
          <span className="badge">{picked.type}</span>{" "}
          <span className="mono">{picked.id}</span> · {picked.label}
          {picked.primary ? " · primary entity" : ""}
        </p>
      )}
    </section>
  );
}
