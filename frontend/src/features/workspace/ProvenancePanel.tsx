import type { CaseProvenance } from "../../api/types";
import { findingCopy } from "../../lib/plainLanguage";
import { SourceList } from "./EvidenceStory";

export function CaseLineage({ provenance }: { provenance: CaseProvenance }) {
  const grouping = provenance.grouping;
  return (
    <section className="lineage">
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
            <strong>{step.name}</strong>
            <p>{step.detail}</p>
          </li>
        ))}
      </ol>
      {provenance.data_sources?.length ? (
        <>
          <p className="muted">Files used</p>
          <SourceList tables={provenance.data_sources} />
        </>
      ) : null}
    </section>
  );
}
