import type { RankFactors } from "../../api/types";
import { Bar, BarChart, CartesianGrid, Cell, LabelList, ReferenceLine, Tooltip, XAxis, YAxis } from "recharts";
import { token } from "../../lib/theme";
import { axisTitle, categoryAxis, chartTheme, valueAxis } from "../../lib/chartTheme";
import { ChartFrame, ChartLegend, ChartPlot } from "./ChartFrame";
import { TooltipCard } from "./ChartTooltip";
import { FACTOR_COLOR_TOKEN, factorData, type FactorDatum, type FactorKey } from "./factorData";

function pts(value: number): string {
  return value.toFixed(1);
}

function labelPts(value: unknown): string {
  const n = typeof value === "number" ? value : Number(value);
  return Number.isFinite(n) ? pts(n) : "";
}

interface FactorContributionChartProps {
  factors: RankFactors;
  labels?: Partial<Record<FactorKey, string>>;
  title?: string;
  height?: number;
  /** Suspicion percent from the case header, so the summary can say it is a different number. */
  suspicionPts?: number | null;
}

/** Desk-rank mix. Bar length is rank points; the number in parentheses is the case-file score. */
export function FactorContributionChart({
  factors,
  labels,
  title = "How desk rank is built",
  height = 240,
  suspicionPts,
}: FactorContributionChartProps) {
  const ranked = [...factorData(factors, labels)].sort((a, b) => b.points - a.points);
  const weighted = ranked.every((d) => d.weight !== null);
  const fromParts = ranked.reduce((sum, d) => sum + d.points, 0);
  const total = weighted ? fromParts : Math.min(99, Math.max(0, factors.composite * 100));
  const top = ranked[0];
  const t = chartTheme();
  const suspicionBit =
    suspicionPts != null ? ` Suspicion on the header is ${suspicionPts} — a separate model score, not this rank.` : "";

  const summary = weighted
    ? `Desk rank ${pts(total)} of 100. ${top.label} on this case is ${top.scorePts} and adds ${pts(top.points)} rank points because it is weighted highest.${suspicionBit}`
    : `Case scores out of 100. Desk rank ${pts(total)} of 100.${suspicionBit}`;

  return (
    <ChartFrame
      title={title}
      summary={summary}
      legend={
        <ChartLegend
          items={ranked.map((d) => ({
            label: `${d.label} ${d.scorePts} on the case · ${pts(d.points)} rank pts`,
            color: token(FACTOR_COLOR_TOKEN[d.key]),
          }))}
        />
      }
      footnote={
        weighted
          ? "Number in parentheses is the case score (same scale as the tiles). Bar length is rank points after weights. Those points add up to desk rank. Desk rank is not suspicion."
          : "Showing raw factor scores (weights missing from the API response)."
      }
      table={{
        caption: "Case scores and how they mix into desk rank",
        columns: weighted ? ["Factor", "On this case", "Rank points"] : ["Factor", "On this case"],
        rows: [
          ...ranked.map((d) => (weighted ? [d.label, d.scorePts, pts(d.points)] : [d.label, d.scorePts])),
          ...(weighted ? [["Desk rank", "—", pts(total)]] : []),
        ],
      }}
    >
      <p className="rank-stack-kicker muted">Share of desk rank {pts(total)} of 100</p>
      <div className="rank-stack" role="img" aria-label={`Desk rank ${pts(total)} of 100`}>
        {ranked.map((d) => (
          <i
            key={d.key}
            style={{ width: `${d.points}%`, background: token(FACTOR_COLOR_TOKEN[d.key]) }}
            title={`${d.label}: ${d.scorePts} on the case, ${pts(d.points)} rank points`}
          />
        ))}
      </div>
      <p className="rank-stack-total">
        <span className="mono num">{pts(total)}</span>
        <span className="muted"> desk rank of 100</span>
      </p>
      <ChartPlot height={height}>
        <BarChart
          data={ranked}
          layout="vertical"
          barCategoryGap="28%"
          margin={{ top: 4, right: 56, bottom: 8, left: 4 }}
          accessibilityLayer
          title={title}
        >
          <CartesianGrid horizontal={false} stroke={t.grid} />
          <XAxis
            type="number"
            {...valueAxis(t)}
            domain={[0, 100]}
            ticks={[0, 25, 50, 75, 100]}
            tickFormatter={(value: number) => String(value)}
            label={{
              ...axisTitle(t, "Rank points (add up to desk rank)"),
              position: "insideBottomLeft",
              offset: -4,
            }}
          />
          <YAxis type="category" dataKey="axisLabel" width={176} reversed {...categoryAxis(t)} />
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
                    { label: "On this case", value: String(datum.scorePts) },
                    { label: "Rank points", value: `${pts(datum.points)} of ${pts(total)}`, color: t.focus },
                    ...(datum.weight !== null ? [{ label: "Weight", value: datum.weight.toFixed(2) }] : []),
                  ]}
                />
              );
            }}
          />
          <Bar dataKey="points" radius={[0, 2, 2, 0]} isAnimationActive={false} maxBarSize={22}>
            {ranked.map((d) => (
              <Cell key={d.key} fill={token(FACTOR_COLOR_TOKEN[d.key])} />
            ))}
            <LabelList dataKey="points" position="right" formatter={labelPts} fill={t.text} fontSize={12} fontWeight={500} />
          </Bar>
        </BarChart>
      </ChartPlot>
    </ChartFrame>
  );
}
