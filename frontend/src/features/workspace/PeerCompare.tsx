import type { PeerGroup } from "../../api/types";

function num(value: unknown): string {
  if (typeof value === "number") return value.toLocaleString(undefined, { maximumFractionDigits: 3 });
  return "—";
}

export function PeerCompare({ evidence }: { evidence: Record<string, unknown> }) {
  const group = (evidence.peer_group ?? null) as PeerGroup | null;
  if (!group) return null;
  const limited = group.confidence === "limited" || group.confidence === "insufficient";
  return (
    <div className={`peer-compare ${limited ? "is-limited" : ""}`}>
      <p className="kicker">Peer comparison · like with like</p>
      <dl>
        <div>
          <dt>This provider</dt>
          <dd className="mono">{num(evidence.provider_value)}</dd>
        </div>
        <div>
          <dt>Peer median</dt>
          <dd className="mono">{num(evidence.peer_median)}</dd>
        </div>
        <div>
          <dt>Peer IQR</dt>
          <dd className="mono">
            {num(evidence.peer_q1)} – {num(evidence.peer_q3)}
          </dd>
        </div>
        <div>
          <dt>Peers</dt>
          <dd className="mono">{group.n_peers}</dd>
        </div>
      </dl>
      <p>
        Group: {group.selection}. Dimensions:{" "}
        {(group.dimensions_used ?? []).join(", ") || "none"}. Geography {group.geography ?? "—"}.
      </p>
      {group.limitation ? <p className="muted">{group.limitation}</p> : null}
      <p className="muted">A difference from peers is a reason to examine the evidence, not a finding of fraud.</p>
    </div>
  );
}
