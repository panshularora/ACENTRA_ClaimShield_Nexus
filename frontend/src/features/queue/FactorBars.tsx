import type { RankFactors } from "../../api/types";
import { pct } from "../../lib/format";

const LABELS: { key: keyof Pick<RankFactors, "severity" | "exposure" | "member" | "evidence" | "urgency">; label: string }[] = [
  { key: "severity", label: "Severity" },
  { key: "exposure", label: "Exposure" },
  { key: "member", label: "Members" },
  { key: "evidence", label: "Evidence" },
  { key: "urgency", label: "Urgency" },
];

export function FactorBars({ factors, compact = false }: { factors?: RankFactors; compact?: boolean }) {
  if (!factors) return <span className="muted">—</span>;
  return (
    <ul className={`factor-bars ${compact ? "compact" : ""}`} aria-label="Ranking factors">
      {LABELS.map((item) => {
        const value = factors[item.key] ?? 0;
        return (
          <li key={item.key}>
            <span>{item.label}</span>
            <span className="factor-track" aria-hidden="true">
              <i style={{ width: `${Math.round(value * 100)}%` }} />
            </span>
            <span className="mono">{pct(value)}</span>
          </li>
        );
      })}
      {!compact && (
        <li className="factor-composite">
          <span>Combined</span>
          <strong className="mono">{pct(factors.composite)}</strong>
        </li>
      )}
    </ul>
  );
}
