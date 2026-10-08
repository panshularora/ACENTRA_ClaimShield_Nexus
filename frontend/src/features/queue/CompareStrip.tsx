import type { QueueCase, RankingPolicy } from "../../api/types";
import { LaneBadge } from "../../components/Badge";
import { Panel } from "../../components/ui/Panel";
import { hours, money, screeningLabel, whyPriority } from "../../lib/format";
import { SCORE_LABELS } from "../../lib/scoreLabels";
import { FactorBars } from "./FactorBars";

/** Side-by-side rank breakdown for up to two queued cases. */
export function CompareStrip({ rows, policy, onClear }: { rows: QueueCase[]; policy?: RankingPolicy; onClear: () => void }) {
  return (
    <Panel
      id="compare"
      eyebrow="Compare"
      title="Rank factors side by side"
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
            <dl className="facts">
              <div>
                <dt>{SCORE_LABELS.expectedValue.label}</dt>
                <dd className="num">{money(row.expected_value ?? 0)}</dd>
              </div>
              <div>
                <dt>Harm</dt>
                <dd className="num">{row.harm}</dd>
              </div>
              <div>
                <dt>Hours</dt>
                <dd className="num">{hours(row.estimated_hours)}</dd>
              </div>
              <div>
                <dt>45-day screen</dt>
                <dd>{screeningLabel(row.screening_days_left)}</dd>
              </div>
            </dl>
            <FactorBars factors={row.rank_factors} policy={policy} title={`Rank drivers · ${row.case_id}`} />
            <p className="muted">{whyPriority(row)}</p>
          </article>
        ))}
      </div>
    </Panel>
  );
}
