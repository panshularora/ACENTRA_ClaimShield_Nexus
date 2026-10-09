import type { QueueCase } from "../api/types";

/** Harm first, then combined rank. Length matches the slots slider. */
export function rankedToday(rows: QueueCase[], slots: number): QueueCase[] {
  const cap = Math.max(1, Math.floor(slots) || 1);
  const pool = rows.filter((row) => row.lane !== "needs_evidence");
  const score = (row: QueueCase) => row.rank_factors?.composite ?? 0;
  const harm = pool
    .filter((row) => row.lane === "harm_priority")
    .sort((a, b) => score(b) - score(a));
  const rest = pool
    .filter((row) => row.lane !== "harm_priority")
    .sort((a, b) => score(b) - score(a));
  return [...harm, ...rest].slice(0, cap);
}
