import type { CaseBrief, Cite } from "../../api/types";

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
        <p className="kicker">Panel 2</p>
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
