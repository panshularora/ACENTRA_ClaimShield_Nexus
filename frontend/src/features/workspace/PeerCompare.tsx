import type { PeerGroup } from "../../api/types";
import { PeerComparisonChart } from "../../components/charts/PeerComparisonChart";
import { peerStats } from "./peerStats";

/** Provider-vs-peer chart plus how the peer group was chosen and its limits. */
export function PeerCompare({ evidence }: { evidence: Record<string, unknown> }) {
  const group = (evidence.peer_group ?? null) as PeerGroup | null;
  if (!group) return null;
  const stats = peerStats(evidence);
  const limited = group.confidence === "limited" || group.confidence === "insufficient";
  return (
    <div className={`peer-compare subpanel ${limited ? "is-limited" : ""}`}>
      {stats ? (
        <PeerComparisonChart stats={stats} />
      ) : (
        <p className="muted">
          Peer statistics (provider value, median, quartiles) were not included in this alert, so no chart is drawn.
        </p>
      )}
      <p className="peer-group-text">
        Peer group: {group.selection}. Dimensions: {(group.dimensions_used ?? []).join(", ") || "none"}
        {group.geography ? ` · ${group.geography}` : ""}
        {group.confidence ? (
          <>
            {" "}
            · <span className={`badge ${limited ? "tone-warning" : "tone-success"}`}>{group.confidence} confidence</span>
          </>
        ) : null}
      </p>
      {group.limitation ? <p className="muted">{group.limitation}</p> : null}
      <p className="muted">A difference from peers is a reason to examine the evidence, not a finding.</p>
    </div>
  );
}
