import { pct, pctNumber } from "../lib/format";

/** Evidence-strength meter (0–1) with the value as text; below 0.40 is styled as weak. Never prints 100%. */
export function EvidenceBar({ value, label = "Evidence strength" }: { value: number; label?: string }) {
  const n = pctNumber(value) ?? 0;
  return (
    <span
      className={`evidence ${value < 0.4 ? "is-weak" : ""}`}
      role="meter"
      aria-label={label}
      aria-valuemin={0}
      aria-valuemax={99}
      aria-valuenow={n}
      aria-valuetext={pct(value)}
    >
      <span className="evidence-track" aria-hidden="true">
        <span className="evidence-fill" style={{ transform: `scaleX(${n / 99})` }} />
      </span>
      <span className="mono num">{pct(value)}</span>
    </span>
  );
}
