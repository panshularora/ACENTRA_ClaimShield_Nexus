import type { RankFactors, RankingPolicy } from "../../api/types";
import { FactorContributionChart } from "../../components/charts/FactorContributionChart";
import { FACTOR_KEYS, policyLabels } from "../../components/charts/factorData";
import { pctNumber } from "../../lib/format";

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
