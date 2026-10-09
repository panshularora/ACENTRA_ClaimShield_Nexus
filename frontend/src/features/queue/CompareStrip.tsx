import type { QueueCase, RankingPolicy } from "../../api/types";
import { LaneBadge } from "../../components/Badge";
import { CaseAxes } from "../../components/CaseAxes";
import { Panel } from "../../components/ui/Panel";
import { whyPriority } from "../../lib/format";
import { FactorBars } from "./FactorBars";

/** Side-by-side rank breakdown for up to two queued cases. */
export function CompareStrip({ rows, policy, onClear }: { rows: QueueCase[]; policy?: RankingPolicy; onClear: () => void }) {
  return (
    <Panel
      id="compare"
      eyebrow="Compare"
      title="Why these cases rank this way"
      actions={
        <button type="button" className="btn small" onClick={onClear}>
          Clear
        </button>
      }
    >
      <div className={`compare-grid n-${rows.length}`}>
        {rows.map((row) => (
          <article key={row.case_id} className="subpanel">
            <div className="chip-row">
              <strong className="mono">{row.case_id}</strong>
              <LaneBadge lane={row.lane} />
            </div>
            <p className="mono muted">{row.primary_entity_id}</p>
            <CaseAxes data={row} />
            <FactorBars
              factors={row.rank_factors}
              policy={policy}
              suspicion={row.p_confirm}
              title={`Desk rank · ${row.case_id}`}
            />
            <p className="muted">{whyPriority(row)}</p>
          </article>
        ))}
      </div>
    </Panel>
  );
}
