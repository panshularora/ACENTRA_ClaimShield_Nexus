/** Evidence-strength meter (0–1) with the value as text; below 0.40 is styled as weak. */
export function EvidenceBar({ value, label = "Evidence strength" }: { value: number; label?: string }) {
  const pct = Math.max(0, Math.min(100, Math.round(value * 100)));
  return (
    <span
      className={`evidence ${value < 0.4 ? "is-weak" : ""}`}
      role="meter"
      aria-label={label}
      aria-valuemin={0}
      aria-valuemax={100}
      aria-valuenow={pct}
      aria-valuetext={`${pct}%`}
    >
      <span className="evidence-track" aria-hidden="true">
        <span className="evidence-fill" style={{ transform: `scaleX(${pct / 100})` }} />
      </span>
      <span className="mono num">{pct}%</span>
    </span>
  );
}
