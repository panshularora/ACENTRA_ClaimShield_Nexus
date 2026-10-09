import { useId, type ReactElement, type ReactNode } from "react";
import { ResponsiveContainer } from "recharts";
import "./charts.css";

export interface DataTableSpec {
  caption: string;
  columns: string[];
  rows: (string | number)[][];
}

interface ChartFrameProps {
  title: string;
  /** One or two sentences that state what the chart shows, for everyone. */
  summary: ReactNode;
  /** Same data as the chart, for keyboard and screen-reader users. */
  table: DataTableSpec;
  legend?: ReactNode;
  footnote?: ReactNode;
  className?: string;
  children: ReactNode;
}

/**
 * Wraps a chart with a title, a text summary, an optional legend and a
 * collapsible data table. Recharts' accessibility layer makes the plot focusable
 * (arrow keys step through the data); the summary and table carry the same
 * information for screen readers.
 */
export function ChartFrame({ title, summary, table, legend, footnote, className, children }: ChartFrameProps) {
  const titleId = useId();
  const summaryId = useId();
  return (
    <figure className={`chart ${className ?? ""}`} aria-labelledby={titleId} aria-describedby={summaryId}>
      <figcaption className="chart-head">
        <span id={titleId} className="chart-title">
          {title}
        </span>
        <span id={summaryId} className="chart-summary">
          {summary}
        </span>
      </figcaption>
      {legend}
      <div className="chart-plot">
        {children}
      </div>
      {footnote ? <p className="chart-footnote">{footnote}</p> : null}
      <details className="chart-table">
        <summary>View as table</summary>
        <div className="table-wrap">
          <table className="grid">
            <caption>{table.caption}</caption>
            <thead>
              <tr>
                {table.columns.map((column, i) => (
                  <th key={column} scope="col" className={i > 0 ? "num" : undefined}>
                    {column}
                  </th>
                ))}
              </tr>
            </thead>
            <tbody>
              {table.rows.map((row, r) => (
                <tr key={r}>
                  {row.map((cell, c) =>
                    c === 0 ? (
                      <th key={c} scope="row">
                        {cell}
                      </th>
                    ) : (
                      <td key={c} className="num">
                        {cell}
                      </td>
                    ),
                  )}
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </details>
    </figure>
  );
}

export interface LegendItem {
  label: string;
  color: string;
  shape?: "square" | "line" | "dashed" | "dot";
}

/** Static legend (Recharts' built-in legend is not keyboard/AT friendly). */
/**
 * Sized plot so Recharts does not start at −1×−1 inside a CSS grid and stay
 * stuck there until a later resize.
 */
export function ChartPlot({ height, children }: { height: number; children: ReactElement }) {
  return (
    <ResponsiveContainer
      width="100%"
      height={height}
      minWidth={0}
      minHeight={height}
      initialDimension={{ width: 480, height }}
    >
      {children}
    </ResponsiveContainer>
  );
}

export function ChartLegend({ items }: { items: LegendItem[] }) {
  return (
    <ul className="chart-legend">
      {items.map((item) => (
        <li key={item.label}>
          <span
            className={`chart-swatch shape-${item.shape ?? "square"}`}
            style={{ color: item.color }}
            aria-hidden="true"
          />
          {item.label}
        </li>
      ))}
    </ul>
  );
}
