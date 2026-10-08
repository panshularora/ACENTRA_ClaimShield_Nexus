import type { CaseBrief, Cite, MatchedPrecedent } from "../../api/types";

function PrecedentList({
  hits,
  onCite,
}: {
  hits: MatchedPrecedent[];
  onCite: (cite: Cite) => void;
}) {
  if (hits.length === 0) return null;
  return (
    <article className="brief-section precedent-hits">
      <h3>Approved precedents</h3>
      {hits.map((hit) => (
        <div key={hit.page_id} className="precedent-hit">
          <p>
            <strong>{hit.title}</strong>{" "}
            <button
              type="button"
              className="cite"
              onClick={() => onCite({ id: hit.citation, kind: "precedent", label: hit.title })}
            >
              {hit.citation}
            </button>
          </p>
          <p>{hit.why_it_matches}</p>
          <ul className="compact-list">
            {hit.matching_facts.map((fact) => (
              <li key={fact}>{fact}</li>
            ))}
          </ul>
          <p className="muted">
            Source {hit.source_case ?? "—"}
            {hit.decision ? ` · ${hit.decision}` : ""}
          </p>
        </div>
      ))}
    </article>
  );
}

export function BriefPanel({
  brief,
  loading,
  error,
  onCite,
}: {
  brief: CaseBrief | undefined;
  loading: boolean;
  error: string | null;
  onCite: (cite: Cite) => void;
}) {
  return (
    <section className="ws-panel ws-brief" aria-labelledby="brief-title">
      <header className="ws-panel-head">
        <p className="kicker">Brief</p>
        <h2 id="brief-title">Investigation brief</h2>
        {brief && (
          <span className="badge">{brief.generator === "template" ? "Template" : "LLM"}</span>
        )}
      </header>
      {loading && <p className="muted">Assembling brief from stored evidence…</p>}
      {error && <p className="error-text">{error}</p>}
      {brief && (
        <div className="brief-body">
          <p className="brief-action">{brief.action}</p>
          <PrecedentList hits={brief.precedents ?? []} onCite={onCite} />
          {brief.sections.map((section) => (
            <article key={section.title} className="brief-section">
              <h3>{section.title}</h3>
              {section.sentences.map((sentence, i) => (
                <p key={i}>
                  {sentence.text}{" "}
                  {sentence.cites.map((cite) => (
                    <button
                      key={cite.id}
                      type="button"
                      className="cite"
                      onClick={() => onCite(cite)}
                    >
                      {cite.label}
                    </button>
                  ))}
                </p>
              ))}
            </article>
          ))}
          <p className="muted">
            Validator: {brief.validator.cited}/{brief.validator.checked} sentences cited,{" "}
            {brief.validator.dropped} dropped.
          </p>
        </div>
      )}
    </section>
  );
}
