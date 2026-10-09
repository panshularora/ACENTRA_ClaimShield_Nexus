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
          We do not have enough similar-provider numbers to draw a comparison chart.
        </p>
      )}
      <p className="peer-group-text">
        Compared with {group.n_peers} similar providers
        {group.specialty ? ` in ${group.specialty.replaceAll("_", " ")}` : ""}
        {group.geography ? `, ${group.geography}` : ""}.
        {limited ? " The comparison group is small, so treat the chart as a hint." : ""}
      </p>
      {group.limitation ? <p className="muted">{group.limitation}</p> : null}
      <p className="muted">Looking different from similar providers is a reason to open the claims, not a conclusion.</p>
    </div>
  );
}
