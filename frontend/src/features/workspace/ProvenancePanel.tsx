import type { AlertLineage, CaseProvenance } from "../../api/types";

export function CaseLineage({ provenance }: { provenance: CaseProvenance }) {
  const grouping = provenance.grouping;
  return (
    <section className="lineage" aria-labelledby="lineage-title">
      <h3 id="lineage-title">How this case was built</h3>
      {provenance.urgent.length > 0 && (
        <div className="banner warn">
          <p>
            <strong>Urgent signals still visible inside this group</strong>
          </p>
          <ul>
            {provenance.urgent.map((item) => (
              <li key={item.alert_id}>
                <span className="mono">{item.rule_id ?? item.kind}</span> {item.label} ·{" "}
                {item.line_ids.length} claim line(s)
              </li>
            ))}
          </ul>
        </div>
      )}
      <p>{grouping.text}</p>
      <p className="muted">
        {grouping.alert_count} alert{grouping.alert_count === 1 ? "" : "s"} ·{" "}
        {grouping.entity_ids.length} NPI{grouping.entity_ids.length === 1 ? "" : "s"} in the case
        {grouping.comparison_peers_held_out && grouping.comparison_peers_held_out.length > 0
          ? ` · ${grouping.comparison_peers_held_out.length} comparison peer(s) held out`
          : ""}
      </p>
      <ol className="lineage-steps">
        {provenance.steps.map((step) => (
          <li key={step.step}>
            <strong>{step.name}</strong>
            <p>{step.detail}</p>
          </li>
        ))}
      </ol>
      <h4>Source tables</h4>
      <ul className="source-list">
        {provenance.data_sources.map((src) => (
          <li key={src.table}>
            <span className="mono">{src.table}</span>
            <span>{src.role}</span>
          </li>
        ))}
      </ul>
      <p className="note">
        Extract: {provenance.extract}. Ranked suspicion for human review, not a fraud label.
      </p>
    </section>
  );
}

export function AlertLineageBlock({ lineage }: { lineage: AlertLineage }) {
  return (
    <div className="alert-lineage">
      <p>{lineage.method}</p>
      {lineage.how ? <p>{lineage.how}</p> : null}
      {lineage.tables.length > 0 ? (
        <ul className="source-list compact">
          {lineage.tables.map((src) => (
            <li key={src.table}>
              <span className="mono">{src.table}</span>
              <span>{src.role}</span>
            </li>
          ))}
        </ul>
      ) : (
        <p className="muted">Source tables were not recorded for this alert.</p>
      )}
      {lineage.line_ids && lineage.line_ids.length ? (
        <p className="muted">
          {lineage.line_ids.length} supporting claim line{lineage.line_ids.length === 1 ? "" : "s"}
        </p>
      ) : null}
      {lineage.fields_used && lineage.fields_used.length > 0 ? (
        <p className="muted">
          Fields used: <span className="mono">{lineage.fields_used.join(" · ")}</span>
        </p>
      ) : null}
      {lineage.comparison_peers_held_out && lineage.comparison_peers_held_out.length > 0 ? (
        <p className="muted">
          Comparison peers used for scoring, not as co-subjects:{" "}
          <span className="mono">{lineage.comparison_peers_held_out.join(" · ")}</span>
        </p>
      ) : null}
    </div>
  );
}
