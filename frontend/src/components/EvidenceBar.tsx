export function EvidenceBar({ value, label = "Evidence" }: { value: number; label?: string }) {
  const pct = Math.max(0, Math.min(100, Math.round(value * 100)));
  return (
    <div className="evidence" title={`${label} ${pct}%`}>
      <span className="evidence-track" aria-hidden="true">
        <span className="evidence-fill" style={{ width: `${pct}%` }} />
      </span>
      <span className="mono">{pct}%</span>
    </div>
  );
}
