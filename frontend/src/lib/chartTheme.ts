/**
 * Resolved chart colours and shared Recharts axis/grid props (design system §6.1–6.2).
 * Recharts writes colours into SVG attributes, so tokens are resolved to concrete strings.
 */
import { token } from "./theme";

export function chartTheme() {
  return {
    focus: token("--chart-focus"),
    comparison: token("--chart-comparison"),
    comparisonLine: token("--chart-comparison-line"),
    grid: token("--chart-grid"),
    axis: token("--chart-axis"),
    baseline: token("--chart-baseline"),
    label: token("--chart-label"),
    reference: token("--chart-reference"),
    referenceDash: token("--chart-reference-dash"),
    harm: token("--harm-solid"),
    text: token("--color-text"),
    surface: token("--color-surface"),
    hover: token("--color-surface-hover"),
    series: (["--chart-1", "--chart-2", "--chart-3", "--chart-4", "--chart-5"] as const).map(token),
  };
}

export type ChartTheme = ReturnType<typeof chartTheme>;

const FONT_SIZE = 12;

export const axisTick = (t: ChartTheme) => ({ fill: t.label, fontSize: FONT_SIZE });

/** Category axis: 1px axis line with 4px outside ticks. */
export const categoryAxis = (t: ChartTheme) => ({
  tick: axisTick(t),
  tickSize: 4,
  tickMargin: 4,
  axisLine: { stroke: t.axis },
  tickLine: { stroke: t.axis },
});

/** Value axis: no axis line; gridlines carry the scale. */
export const valueAxis = (t: ChartTheme) => ({
  tick: axisTick(t),
  tickCount: 5,
  axisLine: false,
  tickLine: false,
});

/** Axis title: 12px muted, horizontal. */
export const axisTitle = (t: ChartTheme, value: string) => ({ value, fill: t.label, fontSize: FONT_SIZE });
