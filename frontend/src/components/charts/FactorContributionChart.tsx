import type { RankFactors } from "../../api/types";
import { Bar, BarChart, Cell, LabelList, ReferenceLine, ResponsiveContainer, Tooltip, XAxis, YAxis } from "recharts";
import { axisTitle, categoryAxis, chartTheme, valueAxis } from "../../lib/chartTheme";
import { ChartFrame } from "./ChartFrame";
import { TooltipCard } from "./ChartTooltip";
import { factorData, type FactorDatum, type FactorKey } from "./factorData";

function pts(value: number): string {
  return value.toFixed(1);
}

interface FactorContributionChartProps {
  factors: RankFactors;
  labels?: Partial<Record<FactorKey, string>>;
  title?: string;
  height?: number;
}

/** Labelled horizontal bars: how much each ranking factor adds to the combined score. */
export function FactorContributionChart({
  factors,
  labels,
  title = "What drives the rank",
  height = 220,
}: FactorContributionChartProps) {
  // Sorted by contribution, largest first (design system §6.3).
  const data = factorData(factors, labels).sort((a, b) => b.points - a.points);
  const weighted = data.every((d) => d.weight !== null);
  const composite = factors.composite * 100;
  const top = data[0];
  const t = chartTheme();

  const summary = weighted
    ? `Combined rank score ${pts(composite)} of 100. Largest contribution: ${top.label} at ${pts(top.points)} points.`
    : `Factor scores out of 100. The API did not send factor weights, so contributions to the ${pts(composite)}-point combined score cannot be split.`;

  return (
    <ChartFrame
      title={title}
      summary={summary}
      footnote={
        weighted
          ? "Contribution = factor score × policy weight. Bars add up to the combined score."
          : "Showing raw factor scores (weights missing from the API response)."
      }
      table={{
        caption: weighted ? "Contribution of each ranking factor" : "Ranking factor scores",
        columns: weighted ? ["Factor", "Score (%)", "Weight", "Points"] : ["Factor", "Score (%)"],
        rows: data.map((d) =>
          weighted
            ? [d.label, Math.round(d.score * 100), (d.weight ?? 0).toFixed(2), pts(d.points)]
            : [d.label, Math.round(d.score * 100)],
        ),
      }}
    >
      <ResponsiveContainer width="100%" height={height}>
        <BarChart
          data={data}
          layout="vertical"
          barCategoryGap="35%"
          margin={{ top: 4, right: 48, bottom: 20, left: 0 }}
          accessibilityLayer
          title={title}
        >
          <XAxis
            type="number"
            {...valueAxis(t)}
            tick={false}
            domain={[0, weighted ? (max: number) => Math.max(25, Math.ceil(max / 5) * 5) : 100]}
            label={{
              ...axisTitle(t, weighted ? "Points of the 100-point combined score" : "Factor score (0–100)"),
              position: "insideBottomLeft",
              offset: 0,
            }}
          />
          <YAxis type="category" dataKey="label" width={150} {...categoryAxis(t)} />
          <ReferenceLine x={0} stroke={t.baseline} />
          <Tooltip
            cursor={{ fill: t.hover }}
            isAnimationActive={false}
            content={({ active, payload }) => {
              const datum = active ? (payload?.[0]?.payload as FactorDatum | undefined) : undefined;
              if (!datum) return null;
              return (
                <TooltipCard
                  title={datum.label}
                  rows={[
                    { label: "Score", value: `${Math.round(datum.score * 100)} / 100` },
                    ...(datum.weight !== null
                      ? [
                          { label: "Weight", value: datum.weight.toFixed(2) },
                          { label: "Contribution", value: `${pts(datum.points)} pts`, color: t.focus },
                        ]
                      : []),
                  ]}
                />
              );
            }}
          />
          <Bar dataKey="points" radius={[0, 2, 2, 0]} isAnimationActive={false}>
            {data.map((d) => (
              <Cell key={d.key} fill={d.key === top.key ? t.focus : t.comparison} />
            ))}
            <LabelList
              dataKey="points"
              position="right"
              formatter={(value) => (typeof value === "number" ? pts(value) : "")}
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
