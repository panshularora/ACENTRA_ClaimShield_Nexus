import {
  Bar,
  BarChart,
  CartesianGrid,
  Cell,
  ErrorBar,
  LabelList,
  ReferenceLine,
  Tooltip,
  XAxis,
  YAxis,
} from "recharts";
import { axisTitle, categoryAxis, chartTheme, valueAxis } from "../../lib/chartTheme";
import { ChartFrame, ChartLegend, ChartPlot } from "./ChartFrame";
import { TooltipCard } from "./ChartTooltip";

/** Peer statistics exactly as sent in an anomaly alert's evidence payload. */
export interface PeerStats {
  metric: string | null;
  providerValue: number;
  median: number;
  q1: number;
  q3: number;
  min: number | null;
  max: number | null;
  fence: number | null;
  nPeers: number;
}

interface PeerDatum {
  name: string;
  value: number;
  /** [below, above] distance to the IQR edges, for the error bar. */
  iqr?: [number, number];
}

function fmt(value: number): string {
  return value.toLocaleString("en-US", { maximumFractionDigits: 2 });
}

/** This provider vs the typical similar provider, with the middle range of the group. */
export function PeerComparisonChart({ stats }: { stats: PeerStats }) {
  const unit = stats.metric ?? "value";
  const data: PeerDatum[] = [
    { name: "This provider", value: stats.providerValue },
    {
      name: `Typical similar provider (${stats.nPeers})`,
      value: stats.median,
      iqr: [stats.median - stats.q1, stats.q3 - stats.median],
    },
  ];
  const t = chartTheme();
  const provider = t.focus;
  const peer = t.comparison;
  const fence = t.reference;
  const ratio = stats.median > 0 ? stats.providerValue / stats.median : null;
  const domainMax = Math.max(stats.providerValue, stats.q3, stats.fence ?? 0, stats.max ?? 0);

  return (
    <ChartFrame
      title="This provider vs similar providers"
      summary={`This provider: ${fmt(stats.providerValue)}. Typical similar provider: ${fmt(stats.median)} (middle range ${fmt(stats.q1)}–${fmt(stats.q3)}, ${stats.nPeers} providers)${
        ratio !== null ? `, ${fmt(ratio)}× typical` : ""
      }. ${unit}.`}
      legend={
        <ChartLegend
          items={[
            { label: "This provider", color: provider },
            { label: "Typical similar provider, bar = middle range", color: peer },
            ...(stats.fence !== null
              ? [{ label: `Unusual if above ${fmt(stats.fence)}`, color: fence, shape: "dashed" as const }]
              : []),
          ]}
        />
      }
      table={{
        caption: `Compared with similar providers (${unit})`,
        columns: ["Measure", "Value"],
        rows: [
          ["This provider", fmt(stats.providerValue)],
          ["Typical similar provider", fmt(stats.median)],
          ["Lower end of the middle range", fmt(stats.q1)],
          ["Upper end of the middle range", fmt(stats.q3)],
          ...(stats.min !== null ? [["Lowest in the group", fmt(stats.min)] as [string, string]] : []),
          ...(stats.max !== null ? [["Highest in the group", fmt(stats.max)] as [string, string]] : []),
          ...(stats.fence !== null ? [["Unusual if above", fmt(stats.fence)] as [string, string]] : []),
          ["Similar providers", stats.nPeers],
        ],
      }}
    >
      <ChartPlot height={150}>
        <BarChart
          data={data}
          layout="vertical"
          barCategoryGap="35%"
          margin={{ top: 4, right: 56, bottom: 24, left: 0 }}
          accessibilityLayer
          title="This provider vs similar providers"
        >
          <CartesianGrid horizontal={false} stroke={t.grid} />
          <XAxis
            type="number"
            {...valueAxis(t)}
            domain={[0, Math.ceil(domainMax * 1.08) || 1]}
            label={{ ...axisTitle(t, unit), position: "insideBottomLeft", offset: -14 }}
          />
          <YAxis type="category" dataKey="name" width={130} {...categoryAxis(t)} />
          <ReferenceLine x={0} stroke={t.baseline} />
          {stats.fence !== null ? (
            <ReferenceLine
              x={stats.fence}
              stroke={fence}
              strokeDasharray={t.referenceDash}
              strokeWidth={1.5}
              ifOverflow="extendDomain"
            />
          ) : null}
          <Tooltip
            cursor={{ fill: t.hover }}
            isAnimationActive={false}
            content={({ active, payload }) => {
              const datum = active ? (payload?.[0]?.payload as PeerDatum | undefined) : undefined;
              if (!datum) return null;
              return (
                <TooltipCard
                  title={datum.name}
                  rows={[
                    { label: "Value", value: `${fmt(datum.value)} ${stats.metric ?? ""}` },
                    ...(datum.iqr
                      ? [{ label: "Middle range of similar providers", value: `${fmt(stats.q1)}–${fmt(stats.q3)}` }]
                      : []),
                  ]}
                />
              );
            }}
          />
          <Bar dataKey="value" radius={[0, 2, 2, 0]} isAnimationActive={false}>
            <Cell fill={provider} />
            <Cell fill={peer} />
            <ErrorBar dataKey="iqr" direction="x" width={8} stroke={t.baseline} strokeWidth={1.5} />
            <LabelList
              dataKey="value"
              position="right"
              formatter={(value) => {
                const n = typeof value === "number" ? value : Number(value);
                return Number.isFinite(n) ? fmt(n) : "";
              }}
              fill={t.text}
              fontSize={12}
              fontWeight={500}
            />
          </Bar>
        </BarChart>
      </ChartPlot>
    </ChartFrame>
  );
}
