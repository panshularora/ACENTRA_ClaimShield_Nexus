import type { PeerGroup } from "../../api/types";
import type { PeerStats } from "../../components/charts/PeerComparisonChart";

function num(value: unknown): number | null {
  return typeof value === "number" && Number.isFinite(value) ? value : null;
}

/** Reads peer statistics from an anomaly alert's evidence; null when any core value is missing. */
export function peerStats(evidence: Record<string, unknown>): PeerStats | null {
  const group = evidence.peer_group as PeerGroup | undefined;
  const providerValue = num(evidence.provider_value);
  const median = num(evidence.peer_median);
  const q1 = num(evidence.peer_q1);
  const q3 = num(evidence.peer_q3);
  if (!group || providerValue === null || median === null || q1 === null || q3 === null) return null;
  return {
    metric: typeof evidence.metric === "string" ? evidence.metric : null,
    providerValue,
    median,
    q1,
    q3,
    min: num(evidence.peer_min),
    max: num(evidence.peer_max),
    fence: num(evidence.fence),
    nPeers: group.n_peers,
  };
}
