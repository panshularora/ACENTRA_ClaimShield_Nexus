import { useMemo, useState } from "react";
import type { NetworkNode, NetworkPack } from "../../api/types";
import { NetworkGraph } from "../../three/NetworkGraph";
import "./network.css";

const EDGE_KINDS = [
  "rendered",
  "billed",
  "at_facility",
  "owns",
  "referral",
  "shared_location",
  "shared_tin",
  "shared_owner",
  "shared_contact",
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
  const [enabled, setEnabled] = useState<Record<string, boolean>>(() =>
    Object.fromEntries(EDGE_KINDS.map((k) => [k, true])),
  );
  const [picked, setPicked] = useState<NetworkNode | null>(null);

  const kindsPresent = useMemo(() => {
    const set = new Set((pack?.edges ?? []).map((e) => e.kind));
    const known = EDGE_KINDS.filter((k) => set.has(k));
    const extra = [...set].filter((k) => !EDGE_KINDS.includes(k));
    return [...known, ...extra];
  }, [pack]);

  return (
    <section className="ws-panel ws-network" aria-labelledby="net-title">
      <header className="ws-panel-head">
        <div>
          <p className="kicker">Relationships</p>
          <h2 id="net-title">Two-hop neighbourhood</h2>
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
      {pack && pack.nodes.length > 0 && (
        <>
          <div className="n3-host">
            <NetworkGraph
              pack={pack}
              enabled={enabled}
              onSelect={(id, type) => {
                const node = pack.nodes.find((n) => n.id === id) ?? null;
                setPicked(node);
                onSelect(id, type);
              }}
            />
          </div>
          <ul className="net-legend">
            <li><i className="t-provider" /> Provider</li>
            <li><i className="t-member" /> Member</li>
            <li><i className="t-facility" /> Facility</li>
            <li><i className="t-owner" /> Owner</li>
          </ul>
        </>
      )}
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
