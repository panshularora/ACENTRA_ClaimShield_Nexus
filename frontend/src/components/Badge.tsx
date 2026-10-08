import type { Lane } from "../api/types";
import { laneLabel } from "../lib/format";

export function LaneBadge({ lane }: { lane: Lane }) {
  return <span className={`badge lane-${lane}`}>{laneLabel(lane)}</span>;
}

export function StatusBadge({ status }: { status: string }) {
  return <span className="badge status">{status}</span>;
}

export function HarmBadge({ harm }: { harm: number }) {
  return (
    <span className={`badge harm-${harm >= 4 ? "high" : harm >= 3 ? "mid" : "low"}`}>
      Harm {harm}
    </span>
  );
}
