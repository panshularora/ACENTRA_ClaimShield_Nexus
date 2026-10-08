import type { AlertLineage, CaseProvenance } from "../../api/types";
import { findingCopy } from "../../lib/plainLanguage";
import { SourceList } from "./EvidenceStory";

export function CaseLineage({ provenance }: { provenance: CaseProvenance }) {
  const grouping = provenance.grouping;
  return (
    <section className="lineage" aria-labelledby="lineage-title">
      <h3 id="lineage-title">How this case was built</h3>
      <p>
        Paid claims were checked, similar providers were compared, and linked NPIs were grouped. The
        scores only rank work for a person.
      </p>
      {provenance.urgent.length > 0 && (
        <div className="banner warn">
          <p>
            <strong>Urgent signals still visible inside this group</strong>
          </p>
          <ul>
            {provenance.urgent.map((item) => (
              <li key={item.alert_id}>
                {findingCopy(item.kind, item.label).title} · {item.line_ids.length} paid claim line
                {item.line_ids.length === 1 ? "" : "s"}
              </li>
            ))}
          </ul>
        </div>
      )}
      <p>{grouping.text}</p>
      <p className="muted">
        {grouping.alert_count} pattern{grouping.alert_count === 1 ? "" : "s"} ·{" "}
        {grouping.entity_ids.length} provider{grouping.entity_ids.length === 1 ? "" : "s"} in the case
      </p>
      <ol className="lineage-steps">
        {provenance.steps.map((step) => (
          <li key={step.step}>
            <strong>
              {step.step}. {step.name}
            </strong>
            <p>{step.detail}</p>
          </li>
        ))}
      </ol>
      <details className="ev-tech">
        <summary>Technical — extract and tables</summary>
        <p className="mono muted">{provenance.extract}</p>
        <h4>Where the numbers came from</h4>
        <SourceList tables={provenance.data_sources} />
        <p className="note">Scores rank work for a person to review. They do not close the case.</p>
      </details>
    </section>
  );
}

export function AlertLineageBlock({ lineage }: { lineage: AlertLineage }) {
  return (
    <div className="alert-lineage">
      <p>{lineage.method}</p>
      {lineage.how ? <p>{lineage.how}</p> : null}
      {lineage.tables.length > 0 ? (
        <SourceList tables={lineage.tables} compact />
      ) : (
        <p className="muted">We did not record which files fed this pattern.</p>
      )}
      {lineage.line_ids && lineage.line_ids.length ? (
        <p className="muted">
          {lineage.line_ids.length} paid claim line{lineage.line_ids.length === 1 ? "" : "s"}
        </p>
      ) : null}
    </div>
  );
}
