import {
  Bar,
  CartesianGrid,
  ComposedChart,
  Line,
  ReferenceLine,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from "recharts";
import type { ClaimRow, TimelineEvent } from "../../api/types";
import { compactMoney, money, monthLabel, shortDate } from "../../lib/format";
import { categoryAxis, chartTheme, valueAxis } from "../../lib/chartTheme";
import { ChartFrame, ChartLegend } from "./ChartFrame";
import { TooltipCard } from "./ChartTooltip";
import { investigationMarkers, weeklyBuckets, type WeekBucket } from "./timelineData";


function monthTicks(data: WeekBucket[]): number[] {
  const seen = new Set<string>();
  return data
    .filter((d) => {
      const key = monthLabel(d.week);
      if (seen.has(key)) return false;
      seen.add(key);
      return true;
    })
    .map((d) => d.week);
}

interface ClaimsTimelineChartProps {
  rows: ClaimRow[];
  events: TimelineEvent[];
  subjectId: string;
}

/** Weekly paid $ (stacked: case subject vs linked providers) and line counts, with investigation markers. */
export function ClaimsTimelineChart({ rows, events, subjectId }: ClaimsTimelineChartProps) {
  const data = weeklyBuckets(rows, events, subjectId);
  const markers = investigationMarkers(events);
  const t = chartTheme();
  const subject = t.focus;
  const linked = t.comparison;
  const [, stayColor, , lineColor, referralColor] = t.series;
  const markerColor = t.reference;
  const totalPaid = data.reduce((sum, d) => sum + d.subjectPaid + d.linkedPaid, 0);
  const totalLines = data.reduce((sum, d) => sum + d.lines, 0);
  const peak = data.reduce<WeekBucket | null>(
    (best, d) => (!best || d.subjectPaid + d.linkedPaid > best.subjectPaid + best.linkedPaid ? d : best),
    null,
  );
  const hasLinked = data.some((d) => d.linkedPaid > 0);
  const hasActivity = data.some((d) => d.referrals > 0 || d.stays > 0);
  const ticks = monthTicks(data);

  return (
    <ChartFrame
      title="Flagged claim lines over time"
      summary={
        peak
          ? `${totalLines} flagged lines, ${money(totalPaid)} paid, ${shortDate(data[0].week)}–${shortDate(
              data[data.length - 1].week,
            )}. Peak week of ${shortDate(peak.week)}: ${money(peak.subjectPaid + peak.linkedPaid)}.${
              markers.length ? ` ${markers.length} prior-investigation event(s) marked.` : ""
            }`
          : "No dated claim lines."
      }
      legend={
        <ChartLegend
          items={[
            { label: "Paid (USD, left axis) · case subject", color: subject },
            ...(hasLinked ? [{ label: "Paid · linked providers", color: linked }] : []),
            { label: "Claim lines (right axis)", color: lineColor, shape: "line" as const },
            ...(markers.length ? [{ label: "Prior investigation event", color: markerColor, shape: "dashed" as const }] : []),
            ...(hasActivity
              ? [
                  { label: "Referrals per week (lower strip)", color: referralColor },
                  { label: "Facility stays per week (lower strip)", color: stayColor },
                ]
              : []),
          ]}
        />
      }
      footnote="Weeks start on Monday (date of service). Only claim lines attached to this case's alerts are included."
      table={{
        caption: "Weekly flagged claims",
        columns: ["Week of", "Paid · subject ($)", "Paid · linked ($)", "Lines", "Referrals", "Facility stays"],
        rows: data
          .filter((d) => d.lines > 0 || d.referrals > 0 || d.stays > 0)
          .map((d) => [
            shortDate(d.week),
            Math.round(d.subjectPaid),
            Math.round(d.linkedPaid),
            d.lines,
            d.referrals,
            d.stays,
          ]),
      }}
    >
      <ResponsiveContainer width="100%" height={260}>
        <ComposedChart
          data={data}
          syncId="case-timeline"
          margin={{ top: 16, right: 8, bottom: 4, left: 4 }}
          accessibilityLayer title="Flagged claim lines over time"
        >
          <CartesianGrid vertical={false} stroke={t.grid} />
          <XAxis
            dataKey="week"
            ticks={ticks}
            tickFormatter={(value: number) => monthLabel(value)}
            {...categoryAxis(t)}
          />
          <YAxis yAxisId="paid" {...valueAxis(t)} tickFormatter={(value: number) => compactMoney(value)} width={56} />
          <YAxis yAxisId="lines" orientation="right" {...valueAxis(t)} allowDecimals={false} width={36} />
          <ReferenceLine yAxisId="paid" y={0} stroke={t.baseline} />
          {markers.map((marker) => (
            <ReferenceLine
              key={`${marker.week}-${marker.label}`}
              yAxisId="paid"
              x={marker.week}
              stroke={markerColor}
              strokeDasharray={t.referenceDash}
            />
          ))}
          <Tooltip
            cursor={{ fill: t.hover }}
            isAnimationActive={false}
            content={({ active, payload }) => {
              const datum = active ? (payload?.[0]?.payload as WeekBucket | undefined) : undefined;
              if (!datum) return null;
              const weekMarkers = markers.filter((m) => m.week === datum.week);
              return (
                <TooltipCard
                  title={`Week of ${shortDate(datum.week)}`}
                  rows={[
                    { label: "Paid · subject", value: money(datum.subjectPaid), color: subject },
                    ...(hasLinked ? [{ label: "Paid · linked", value: money(datum.linkedPaid), color: linked }] : []),
                    { label: "Claim lines", value: datum.lines, color: lineColor },
                    ...(datum.referrals ? [{ label: "Referrals", value: datum.referrals }] : []),
                    ...(datum.stays ? [{ label: "Facility stays", value: datum.stays }] : []),
                    ...weekMarkers.map((m) => ({ label: "Event", value: m.label, color: markerColor })),
                  ]}
                />
              );
            }}
          />
          <Bar yAxisId="paid" dataKey="subjectPaid" stackId="paid" fill={subject} isAnimationActive={false} />
          {hasLinked ? (
            <Bar yAxisId="paid" dataKey="linkedPaid" stackId="paid" fill={linked} radius={[2, 2, 0, 0]} isAnimationActive={false} />
          ) : null}
          <Line
            yAxisId="lines"
            dataKey="lines"
            type="linear"
            stroke={lineColor}
            strokeWidth={2}
            strokeLinejoin="round"
            dot={false}
            isAnimationActive={false}
          />
        </ComposedChart>
      </ResponsiveContainer>
      {hasActivity ? (
        <ResponsiveContainer width="100%" height={96}>
          <ComposedChart
            data={data}
            syncId="case-timeline"
            margin={{ top: 4, right: 44, bottom: 4, left: 4 }}
            accessibilityLayer title="Referrals and facility stays per week"
          >
            <CartesianGrid vertical={false} stroke={t.grid} />
            <XAxis dataKey="week" ticks={ticks} tickFormatter={(value: number) => monthLabel(value)} hide />
            <YAxis {...valueAxis(t)} tickCount={3} allowDecimals={false} width={56} />
            <Tooltip content={() => null} cursor={{ fill: t.hover }} isAnimationActive={false} />
            <Bar dataKey="referrals" stackId="activity" fill={referralColor} isAnimationActive={false} />
            <Bar dataKey="stays" stackId="activity" fill={stayColor} isAnimationActive={false} />
          </ComposedChart>
        </ResponsiveContainer>
      ) : null}
    </ChartFrame>
  );
}
