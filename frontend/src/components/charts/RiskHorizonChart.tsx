import { Bar, BarChart, CartesianGrid, Cell, LabelList, ResponsiveContainer, Tooltip, XAxis, YAxis } from "recharts";
import { pct } from "../../lib/format";
import { categoryAxis, chartTheme, valueAxis } from "../../lib/chartTheme";
import { ChartFrame } from "./ChartFrame";
import { SCORE_LABELS } from "../../lib/scoreLabels";
import { TooltipCard } from "./ChartTooltip";

interface HorizonDatum {
  horizon: string;
  value: number | null;
}

interface RiskHorizonChartProps {
  f30: number | null;
  f60: number | null;
  f90: number | null;
  /** The horizon (days) the queue currently ranks on; that bar is emphasised. */
  appliedHorizon?: number;
}

/** 30/60/90-day cumulative risk scores from the API as labelled bars on a 0–100% scale. */
export function RiskHorizonChart({ f30, f60, f90, appliedHorizon }: RiskHorizonChartProps) {
  const data: HorizonDatum[] = [
    { horizon: "30 days", value: f30 },
    { horizon: "60 days", value: f60 },
    { horizon: "90 days", value: f90 },
  ];
  const missing = data.filter((d) => d.value === null).map((d) => d.horizon);
  const t = chartTheme();

  return (
    <ChartFrame
      className="is-compact"
      title={SCORE_LABELS.horizon.chartTitle}
      summary={`${SCORE_LABELS.horizon.meaning}: ${data.map((d) => `${d.horizon} ${pct(d.value)}`).join(", ")}.${
        missing.length ? ` No score sent for ${missing.join(", ")}.` : ""
      }`}
      table={{
        caption: SCORE_LABELS.horizon.chartTitle,
        columns: ["Horizon", "Risk (%)"],
        rows: data.map((d) => [d.horizon, d.value === null ? "Not provided" : Math.round(d.value * 100)]),
      }}
    >
      <ResponsiveContainer width="100%" height={132}>
        <BarChart
          data={data}
          barCategoryGap="35%"
          margin={{ top: 18, right: 4, bottom: 0, left: -12 }}
          accessibilityLayer
          title={SCORE_LABELS.horizon.chartTitle}
        >
          <CartesianGrid vertical={false} stroke={t.grid} />
          <XAxis dataKey="horizon" {...categoryAxis(t)} />
          <YAxis
            {...valueAxis(t)}
            domain={[0, 1]}
            ticks={[0, 0.5, 1]}
            tickFormatter={(value: number) => `${Math.round(value * 100)}%`}
            width={44}
          />
          <Tooltip
            cursor={{ fill: t.hover }}
            isAnimationActive={false}
            content={({ active, payload }) => {
              const datum = active ? (payload?.[0]?.payload as HorizonDatum | undefined) : undefined;
              if (!datum) return null;
              return <TooltipCard title={`${datum.horizon} horizon`} rows={[{ label: SCORE_LABELS.horizon.tooltip, value: pct(datum.value) }]} />;
            }}
          />
          <Bar dataKey="value" radius={[2, 2, 0, 0]} isAnimationActive={false}>
            {data.map((d) => (
              <Cell key={d.horizon} fill={appliedHorizon && d.horizon.startsWith(String(appliedHorizon)) ? t.focus : t.comparison} />
            ))}
            <LabelList
              dataKey="value"
              position="top"
              formatter={(value) => (typeof value === "number" ? pct(value) : "n/a")}
              fill={t.text}
              fontSize={12}
              fontWeight={500}
            />
          </Bar>
        </BarChart>
      </ResponsiveContainer>
    </ChartFrame>
  );
}
