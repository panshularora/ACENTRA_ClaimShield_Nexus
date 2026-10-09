import type { Lane } from "../../api/types";
import { LANE_ORDER, laneLabel } from "../../lib/format";

const LANE_COLOR: Record<Lane, string> = {
  harm_priority: "#94296f",
  selected: "#3b82f6",
  needs_evidence: "#94a3b8",
  overflow: "#cbd5e1",
};

const SPARK: Record<string, string> = {
  blue: "#60a5fa",
  amber: "#f59e0b",
  orange: "#fb7185",
  plum: "#e879a8",
};

function Spark({ values, tone }: { values: number[]; tone: string }) {
  if (values.length < 2) return null;
  const min = Math.min(...values);
  const max = Math.max(...values);
  const span = max - min || 1;
  const w = 92;
  const h = 36;
  const d = values
    .map((v, i) => {
      const x = (i / (values.length - 1)) * w;
      const y = h - ((v - min) / span) * (h - 6) - 3;
      return `${i === 0 ? "M" : "L"}${x.toFixed(1)} ${y.toFixed(1)}`;
    })
    .join(" ");
  return (
    <svg className="dash-spark" viewBox={`0 0 ${w} ${h}`} aria-hidden="true">
      <path d={d} fill="none" stroke={SPARK[tone] ?? SPARK.blue} strokeWidth="2.2" strokeLinecap="round" />
    </svg>
  );
}

interface KpiCardProps {
  label: string;
  hint: string;
  value: string | number;
  tone?: "blue" | "amber" | "orange" | "plum";
  spark?: number[];
  pressed?: boolean;
  onSelect?: () => void;
}

export function KpiCard({
  label,
  hint,
  value,
  tone = "blue",
  spark,
  pressed,
  onSelect,
}: KpiCardProps) {
  const inner = (
    <>
      <div className="dash-kpi-head">
        <span className="dash-kpi-mark" aria-hidden="true" />
        <div>
          <h3>{label}</h3>
          <p>{hint}</p>
        </div>
      </div>
      <div className="dash-kpi-foot">
        <p className="dash-kpi-value">{value}</p>
        {spark && spark.length > 1 ? <Spark values={spark} tone={tone} /> : null}
      </div>
    </>
  );

  if (onSelect) {
    return (
      <button
        type="button"
        className={`dash-kpi tone-${tone} is-btn`}
        aria-pressed={pressed}
        onClick={onSelect}
      >
        {inner}
      </button>
    );
  }

  return <article className={`dash-kpi tone-${tone}`}>{inner}</article>;
}

interface LaneMixCardProps {
  casesByLane: Record<Lane, number>;
  selected: Lane | "all";
  onSelect: (lane: Lane) => void;
}

/** Donut of today's lanes — same four buckets as the queue. */
export function LaneMixCard({ casesByLane, selected, onSelect }: LaneMixCardProps) {
  const total = LANE_ORDER.reduce((sum, lane) => sum + casesByLane[lane], 0) || 1;
  const onDesk = casesByLane.harm_priority + casesByLane.selected;
  let angle = 0;
  const slices = LANE_ORDER.map((lane) => {
    const start = angle;
    const sweep = (casesByLane[lane] / total) * 360;
    angle += sweep;
    return { lane, start, sweep, n: casesByLane[lane] };
  });

  return (
    <article className="dash-wide">
      <div className="dash-kpi-head">
        <span className="dash-kpi-mark tone-mix" aria-hidden="true" />
        <div>
          <h3>Today&apos;s mix</h3>
          <p>Harm first, then rank, then backlog</p>
        </div>
      </div>
      <div className="lane-mix">
        <div className="lane-mix-chart">
          <svg viewBox="0 0 120 120" aria-hidden="true">
            {slices.map((slice) =>
              slice.sweep <= 0 ? null : (
                <circle
                  key={slice.lane}
                  cx="60"
                  cy="60"
                  r="38"
                  fill="none"
                  stroke={LANE_COLOR[slice.lane]}
                  strokeWidth="16"
                  strokeDasharray={`${(slice.sweep / 360) * 238.8} 238.8`}
                  strokeDashoffset={-((slice.start / 360) * 238.8)}
                  transform="rotate(-90 60 60)"
                />
              ),
            )}
          </svg>
          <div className="lane-mix-center">
            <strong>{onDesk}</strong>
            <span>today</span>
          </div>
        </div>
        <ul className="lane-mix-legend">
          {LANE_ORDER.map((lane) => (
            <li key={lane}>
              <button type="button" aria-pressed={selected === lane} onClick={() => onSelect(lane)}>
                <i style={{ background: LANE_COLOR[lane] }} aria-hidden="true" />
                <span>{laneLabel(lane)}</span>
                <strong>{casesByLane[lane]}</strong>
              </button>
            </li>
          ))}
        </ul>
      </div>
    </article>
  );
}

interface SlotFillCardProps {
  filled: number;
  slots: number;
}

/** One dot per slot on today's recommended queue. */
export function SlotFillCard({ filled, slots }: SlotFillCardProps) {
  const cap = Math.max(1, slots);
  const used = Math.min(filled, cap);

  return (
    <article className="dash-wide">
      <div className="dash-kpi-head">
        <span className="dash-kpi-mark tone-fill" aria-hidden="true" />
        <div>
          <h3>Today&apos;s slots</h3>
          <p>Ranked cases on the queue</p>
        </div>
        <span className="dash-fill-chip">
          {used}/{cap}
        </span>
      </div>
      <p className="dash-kpi-value">{used}</p>
      <p className="dash-kpi-sub">of {cap} investigator slots</p>
      <div className="dash-dots is-slots" aria-hidden="true">
        {Array.from({ length: cap }, (_, i) => (
          <span key={i} className={i < used ? "is-on" : ""} />
        ))}
      </div>
      <div className="dash-fill-foot">
        <span>Filled</span>
        <span>Open</span>
      </div>
    </article>
  );
}

