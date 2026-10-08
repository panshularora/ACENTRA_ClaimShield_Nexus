import type { ReactNode } from "react";

interface StatTileProps {
  label: string;
  value: ReactNode;
  hint?: ReactNode;
  /** "harm" marks a patient-harm figure with the plum ✚ glyph. */
  tone?: "default" | "harm";
}

/** One labelled figure inside a `.stat-grid` <dl>. */
export function StatTile({ label, value, hint, tone = "default" }: StatTileProps) {
  return (
    <div className={`stat ${tone === "harm" ? "tone-harm" : ""}`}>
      <dt>{label}</dt>
      <dd>{value}</dd>
      {hint ? <dd className="stat-hint">{hint}</dd> : null}
    </div>
  );
}
