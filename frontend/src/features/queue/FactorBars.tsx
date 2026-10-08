import type { RankFactors, RankingPolicy } from "../../api/types";
import { FactorContributionChart } from "../../components/charts/FactorContributionChart";
import {
  DEFAULT_FACTOR_LABELS,
  FACTOR_KEYS,
  factorData,
  policyLabels,
  type FactorKey,
} from "../../components/charts/factorData";
import { token } from "../../lib/theme";

const STRIP_TOKENS: Record<FactorKey, `--${string}`> = {
  severity: "--chart-6",
  exposure: "--chart-4",
  member: "--chart-5",
  evidence: "--chart-1",
  urgency: "--chart-3",
};


/** Risk-factor contributions as a labelled horizontal bar chart. */
export function FactorBars({
  factors,
  policy,
  title,
}: {
  factors?: RankFactors;
  policy?: RankingPolicy;
  title?: string;
}) {
  if (!factors) {
    return <p className="muted">The API sent no rank factors for this case.</p>;
  }
  return <FactorContributionChart factors={factors} labels={policyLabels(policy)} title={title} />;
}

/**
 * Compact stacked bar for table cells: each segment is one factor's
 * contribution, so the full bar length is the combined score.
 */
export function FactorStrip({ factors }: { factors?: RankFactors }) {
  if (!factors) return <span className="muted">—</span>;
  const data = factorData(factors);
  const description = data.map((d) => `${d.label} ${d.points.toFixed(1)}`).join(", ");
  return (
    <span className="factor-strip" role="img" aria-label={`Combined ${Math.round(factors.composite * 100)} of 100: ${description}`}>
      <span className="factor-strip-track" aria-hidden="true">
        {data.map((d) => (
          <i key={d.key} style={{ width: `${d.points}%`, background: token(STRIP_TOKENS[d.key]) }} title={`${d.label} ${d.points.toFixed(1)}`} />
        ))}
      </span>
      <span className="mono num">{Math.round(factors.composite * 100)}</span>
    </span>
  );
}

/** Legend for FactorStrip colours, shown once above the queue table. */
export function FactorStripLegend() {
  return (
    <ul className="chart-legend factor-strip-legend" aria-label="Factor colours in the rank column">
      {FACTOR_KEYS.map((key) => (
        <li key={key}>
          <span className="chart-swatch" style={{ color: token(STRIP_TOKENS[key]) }} aria-hidden="true" />
          {DEFAULT_FACTOR_LABELS[key]}
        </li>
      ))}
    </ul>
  );
}
