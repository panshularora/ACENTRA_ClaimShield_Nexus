import type { RankFactors } from "../../api/types";
import { pct } from "../../lib/format";

const LABELS: { key: keyof Pick<RankFactors, "severity" | "exposure" | "member" | "evidence" | "urgency">; label: string }[] = [
  { key: "severity", label: "Severity" },
  { key: "exposure", label: "Exposure" },
  { key: "member", label: "Members" },
  { key: "evidence", label: "Evidence" },
  { key: "urgency", label: "Urgency" },
];

export function FactorBars({
  factors,
  compact = false,
  variant,
}: {
  factors?: RankFactors;
  compact?: boolean;
  variant?: "full" | "compact" | "strip";
}) {
  if (!factors) return <span className="muted">—</span>;
  const mode = variant ?? (compact ? "compact" : "full");
  if (mode === "strip") {
    return (
      <ul className="factor-bars strip" aria-label="Ranking factors">
        {LABELS.map((item) => {
          const value = factors[item.key] ?? 0;
          return (
            <li key={item.key} title={`${item.label} ${pct(value)}`}>
              <span className="factor-track" aria-hidden="true">
                <i style={{ width: `${Math.round(value * 100)}%` }} />
              </span>
            </li>
          );
        })}
      </ul>
    );
  }
  return (
    <ul className={`factor-bars ${mode === "compact" ? "compact" : ""}`} aria-label="Ranking factors">
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
      {mode === "full" && (
        <li className="factor-composite">
          <span>Combined</span>
          <span className="factor-track" aria-hidden="true">
            <i style={{ width: `${Math.round((factors.composite ?? 0) * 100)}%` }} />
          </span>
          <strong className="mono">{pct(factors.composite)}</strong>
        </li>
      )}
    </ul>
  );
}
