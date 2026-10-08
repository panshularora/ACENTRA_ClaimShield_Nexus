import type { Lane } from "../api/types";
import { hours as hoursFmt } from "../lib/format";

const LANES: { lane: Lane; label: string; color: string }[] = [
  { lane: "harm_priority", label: "Harm priority", color: "#b94832" },
  { lane: "selected", label: "Selected", color: "#1aa24c" },
  { lane: "needs_evidence", label: "Needs evidence", color: "#5b6d82" },
  { lane: "overflow", label: "Monitor", color: "#8a6d2e" },
];

export function QueueScene({
  hoursByLane,
  selected,
  onSelect,
}: {
  hoursByLane: Record<Lane, number>;
  selected: Lane | "all";
  onSelect: (lane: Lane) => void;
  reduced?: boolean;
}) {
  const maxHours = Math.max(4, ...LANES.map((lane) => hoursByLane[lane.lane] ?? 0));
  const ticks = [0, 0.25, 0.5, 0.75, 1].map((t) => t * maxHours);

  return (
    <figure className="queue-chart">
      <figcaption>
        <div>
          <p className="kicker">Hours by queue lane</p>
          <h2>Where investigator time sits</h2>
        </div>
        <p className="muted">Click a bar to filter the table. Heights stay still.</p>
      </figcaption>
      <svg viewBox="0 0 760 248" role="img" aria-label="Investigation hours by queue lane">
        {ticks.map((tick) => {
          const x = 168 + (tick / maxHours) * 500;
          return (
            <g key={tick}>
              <line x1={x} y1={12} x2={x} y2={216} stroke="#e3eee6" strokeWidth="1" />
              <text x={x} y={236} textAnchor="middle" className="qc-tick">
                {tick.toFixed(0)}h
              </text>
            </g>
          );
        })}
        {LANES.map((lane, i) => {
          const value = hoursByLane[lane.lane] ?? 0;
          const y = 18 + i * 50;
          const width = Math.max(value > 0 ? 10 : 0, (value / maxHours) * 500);
          const active = selected === "all" || selected === lane.lane;
          return (
            <g
              key={lane.lane}
              className={`qc-row ${active ? "on" : "off"}`}
              onClick={() => onSelect(lane.lane)}
              role="button"
              tabIndex={0}
              aria-pressed={selected === lane.lane}
              onKeyDown={(event) => {
                if (event.key === "Enter" || event.key === " ") {
                  event.preventDefault();
                  onSelect(lane.lane);
                }
              }}
            >
              <rect x={0} y={y - 8} width={760} height={46} fill="transparent" />
              <text x={8} y={y + 20} className="qc-label">
                {lane.label}
              </text>
              <rect x={168} y={y} width={500} height={28} rx={8} fill="#eef4f0" />
              {width > 0 && (
                <rect x={168} y={y} width={width} height={28} rx={8} fill={lane.color} opacity={active ? 1 : 0.38} />
              )}
              <text x={680} y={y + 20} className="qc-value">
                {hoursFmt(value)}
              </text>
            </g>
          );
        })}
      </svg>
    </figure>
  );
}
