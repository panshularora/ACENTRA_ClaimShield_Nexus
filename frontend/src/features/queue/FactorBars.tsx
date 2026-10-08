import type { RankFactors, RankingPolicy } from "../../api/types";
import { FactorContributionChart } from "../../components/charts/FactorContributionChart";
import {
  FACTOR_COLOR_TOKEN,
  FACTOR_KEYS,
  SHORT_FACTOR_LABELS,
  factorData,
  policyLabels,
} from "../../components/charts/factorData";
import { pctNumber } from "../../lib/format";
import { token } from "../../lib/theme";


/** Risk-factor contributions as a labelled horizontal bar chart. */
export function FactorBars({
  factors,
  policy,
  title,
  suspicion,
}: {
  factors?: RankFactors;
  policy?: RankingPolicy;
  title?: string;
  suspicion?: number | null;
}) {
  if (!factors) {
    return <p className="muted">The API sent no rank factors for this case.</p>;
  }
  return (
    <FactorContributionChart
      key={`${factors.composite}-${FACTOR_KEYS.map((key) => factors[key]).join("-")}`}
      factors={factors}
      labels={policyLabels(policy)}
      title={title}
      suspicionPts={pctNumber(suspicion)}
    />
  );
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
          <i key={d.key} style={{ width: `${d.points}%`, background: token(FACTOR_COLOR_TOKEN[d.key]) }} title={`${d.label} ${d.points.toFixed(1)}`} />
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
          <span className="chart-swatch" style={{ color: token(FACTOR_COLOR_TOKEN[key]) }} aria-hidden="true" />
          {SHORT_FACTOR_LABELS[key]}
        </li>
      ))}
    </ul>
  );
}
