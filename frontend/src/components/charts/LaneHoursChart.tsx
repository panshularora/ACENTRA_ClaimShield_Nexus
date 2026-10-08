import { Bar, BarChart, CartesianGrid, Cell, LabelList, ReferenceLine, ResponsiveContainer, Tooltip, XAxis, YAxis } from "recharts";
import type { Lane } from "../../api/types";
import { hours, LANE_ORDER, laneLabel } from "../../lib/format";
import { categoryAxis, chartTheme, valueAxis, type ChartTheme } from "../../lib/chartTheme";
import { ChartFrame, ChartLegend } from "./ChartFrame";
import { TooltipCard } from "./ChartTooltip";

/** Harm lane in the harm colour, today's selection as the focus series, the rest gray (§6.3). */
const laneColor = (t: ChartTheme, lane: Lane): string =>
  lane === "harm_priority" ? t.harm : lane === "selected" ? t.focus : t.comparison;

const laneAxisLabel = (lane: Lane): string => (lane === "harm_priority" ? `✚ ${laneLabel(lane)}` : laneLabel(lane));

interface LaneDatum {
  lane: Lane;
  label: string;
  hours: number;
  cases: number;
}

interface LaneHoursChartProps {
  hoursByLane: Record<Lane, number>;
  casesByLane: Record<Lane, number>;
  capacityHours: number;
  selected: Lane | "all";
  onSelect: (lane: Lane) => void;
}

/** Estimated investigator hours per queue lane against team capacity. */
export function LaneHoursChart({ hoursByLane, casesByLane, capacityHours, selected, onSelect }: LaneHoursChartProps) {
  const data: LaneDatum[] = LANE_ORDER.map((lane) => ({
    lane,
    label: laneAxisLabel(lane),
    hours: hoursByLane[lane],
    cases: casesByLane[lane],
  }));
  const desk = hoursByLane.harm_priority + hoursByLane.selected;
  const t = chartTheme();

  return (
    <ChartFrame
      title="Where investigator time sits"
      summary={`Today's desk (harm priority + selected) needs ${hours(desk)} of ${hours(capacityHours)} capacity. ${hours(
        hoursByLane.overflow,
      )} sit on the tracked backlog and ${hours(hoursByLane.needs_evidence)} wait for evidence.`}
      legend={
        <ChartLegend
          items={[
            ...data.map((d) => ({ label: d.label, color: laneColor(t, d.lane) })),
            { label: `Team capacity (${hours(capacityHours)})`, color: t.reference, shape: "dashed" as const },
          ]}
        />
      }
      footnote="Select a bar, or a lane button below, to filter the queue table."
      table={{
        caption: "Estimated hours by lane",
        columns: ["Lane", "Cases", "Hours"],
        rows: data.map((d) => [d.label, d.cases, d.hours.toFixed(1)]),
      }}
    >
      <ResponsiveContainer width="100%" height={200}>
        <BarChart
          data={data}
          layout="vertical"
          barCategoryGap="35%"
          margin={{ top: 20, right: 56, bottom: 0, left: 0 }}
          accessibilityLayer title="Where investigator time sits"
        >
          <CartesianGrid horizontal={false} stroke={t.grid} />
          <XAxis
            type="number"
            {...valueAxis(t)}
            domain={[0, (max: number) => Math.ceil(Math.max(max, capacityHours) * 1.1)]}
            tickFormatter={(value: number) => `${value} h`}
          />
          <YAxis type="category" dataKey="label" width={132} {...categoryAxis(t)} />
          <ReferenceLine x={0} stroke={t.baseline} />
          <ReferenceLine
            x={capacityHours}
            stroke={t.reference}
            strokeDasharray={t.referenceDash}
            strokeWidth={1.5}
            label={{ value: `Capacity ${hours(capacityHours)}`, position: "top", fill: t.label, fontSize: 12 }}
          />
          <Tooltip
            cursor={{ fill: t.hover }}
            isAnimationActive={false}
            content={({ active, payload }) => {
              const datum = active ? (payload?.[0]?.payload as LaneDatum | undefined) : undefined;
              if (!datum) return null;
              return (
                <TooltipCard
                  title={datum.label}
                  rows={[
                    { label: "Cases", value: datum.cases },
                    { label: "Hours", value: hours(datum.hours), color: laneColor(t, datum.lane) },
                  ]}
                />
              );
            }}
          />
          <Bar
            dataKey="hours"
            radius={[0, 2, 2, 0]}
            isAnimationActive={false}
            cursor="pointer"
            onClick={(entry) => {
              const lane = (entry.payload as LaneDatum | undefined)?.lane;
              if (lane) onSelect(lane);
            }}
          >
            {data.map((d) => (
              <Cell
                key={d.lane}
                fill={laneColor(t, d.lane)}
                fillOpacity={selected === "all" || selected === d.lane ? 1 : 0.35}
              />
            ))}
            <LabelList
              dataKey="hours"
              position="right"
              formatter={(value) => (typeof value === "number" ? hours(value) : "")}
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
