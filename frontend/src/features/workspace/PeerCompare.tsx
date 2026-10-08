import type { PeerGroup } from "../../api/types";

function num(value: unknown): string {
  if (typeof value === "number") return value.toLocaleString(undefined, { maximumFractionDigits: 3 });
  return "—";
}

function asNum(value: unknown): number | null {
  return typeof value === "number" && Number.isFinite(value) ? value : null;
}

export function PeerCompare({ evidence }: { evidence: Record<string, unknown> }) {
  const group = (evidence.peer_group ?? null) as PeerGroup | null;
  if (!group) return null;
  const limited = group.confidence === "limited" || group.confidence === "insufficient";
  const provider = asNum(evidence.provider_value);
  const q1 = asNum(evidence.peer_q1);
  const median = asNum(evidence.peer_median);
  const q3 = asNum(evidence.peer_q3);
  return (
    <div className={`peer-compare ${limited ? "is-limited" : ""}`}>
      <p className="kicker">Peer comparison · like with like</p>
      {provider != null && q1 != null && q3 != null && median != null && (
        <PeerRange provider={provider} q1={q1} median={median} q3={q3} />
      )}
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
      <p className="muted">
        A difference from peers is a reason to examine the evidence.
      </p>
    </div>
  );
}

function PeerRange({
  provider,
  q1,
  median,
  q3,
}: {
  provider: number;
  q1: number;
  median: number;
  q3: number;
}) {
  const lo = Math.min(q1, provider, median);
  const hi = Math.max(q3, provider, median);
  const span = hi - lo || 1;
  const pct = (v: number) => `${((v - lo) / span) * 100}%`;
  return (
    <div className="peer-range" aria-hidden="true">
      <span className="peer-iqr" style={{ left: pct(q1), width: `calc(${pct(q3)} - ${pct(q1)})` }} />
      <span className="peer-median" style={{ left: pct(median) }} />
      <span className="peer-dot" style={{ left: pct(provider) }} />
    </div>
  );
}
