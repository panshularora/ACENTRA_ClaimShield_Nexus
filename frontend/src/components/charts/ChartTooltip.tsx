import type { ReactNode } from "react";

export interface TooltipRow {
  label: string;
  value: ReactNode;
  color?: string;
}

/** Shared tooltip body so every chart's hover card looks the same. */
export function TooltipCard({ title, rows }: { title: ReactNode; rows: TooltipRow[] }) {
  return (
    <div className="chart-tooltip">
      <p className="chart-tooltip-title">{title}</p>
      <dl>
        {rows.map((row) => (
          <div key={row.label}>
            <dt>
              {row.color ? <span className="chart-swatch" style={{ color: row.color }} aria-hidden="true" /> : null}
              {row.label}
            </dt>
            <dd>{row.value}</dd>
          </div>
        ))}
      </dl>
    </div>
  );
}
