import type { CaseBrief, Cite, MatchedPrecedent } from "../../api/types";
import { ErrorState, LoadingState } from "../../components/ui/States";

function uniqueBy<T>(items: T[], key: (item: T) => string): T[] {
  const seen = new Set<string>();
  return items.filter((item) => {
    const k = key(item);
    if (seen.has(k)) return false;
    seen.add(k);
    return true;
  });
}

function CiteButton({ cite, match, onCite }: { cite: Cite; match: boolean; onCite: (cite: Cite) => void }) {
  return (
    <button
      type="button"
      className={`cite ${match ? "is-match" : ""}`}
      aria-label={`Open citation ${cite.label}${match ? " (involves the selected entity)" : ""}`}
      onClick={() => onCite(cite)}
    >
      {cite.label}
    </button>
  );
}

function PrecedentList({ hits, onCite }: { hits: MatchedPrecedent[]; onCite: (cite: Cite) => void }) {
  if (hits.length === 0) return null;
  return (
    <article className="brief-section">
      <h3>Approved precedents</h3>
      {hits.map((hit) => (
        <div key={hit.page_id} className="subpanel">
          <p>
            <strong>{hit.title}</strong>{" "}
            <CiteButton cite={{ id: hit.citation, kind: "precedent", label: hit.citation }} match={false} onCite={onCite} />
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

interface BriefPanelProps {
  brief: CaseBrief | undefined;
  loading: boolean;
  error: unknown;
  onCite: (cite: Cite) => void;
  /** Citation ids that involve the focused network entity, or null for no focus. */
  highlightCiteIds: Set<string> | null;
  focusLabel: string | null;
}

/** Investigation brief where every sentence carries clickable citations to its evidence. */
export function BriefPanel({ brief, loading, error, onCite, highlightCiteIds, focusLabel }: BriefPanelProps) {
  if (loading) return <LoadingState label="Assembling the brief from stored evidence…" />;
  if (error) return <ErrorState title="Brief unavailable" error={error} />;
  if (!brief) return null;
  const isMatch = (cite: Cite) => Boolean(highlightCiteIds?.has(cite.id));
  const matches = brief.sections.reduce(
    (n, section) => n + section.sentences.filter((sentence) => sentence.cites.some(isMatch)).length,
    0,
  );

  return (
    <div className="brief">
      <div className="brief-meta chip-row">
        <span className="badge">{brief.generator === "template" ? "Template brief" : "LLM brief"}</span>
        <span className="badge">
          {brief.validator.cited}/{brief.validator.checked} sentences cited
        </span>
        {brief.validator.dropped > 0 ? <span className="badge tone-warning">{brief.validator.dropped} uncited dropped</span> : null}
      </div>
      {highlightCiteIds ? (
        <p className="banner ok focus-banner">
          {matches > 0
            ? `${matches} sentence${matches === 1 ? "" : "s"} cite evidence involving ${focusLabel}; highlighted below.`
            : `No brief citation points at evidence involving ${focusLabel}.`}
        </p>
      ) : null}
      <p className="brief-action">{brief.action}</p>
      <PrecedentList hits={brief.precedents ?? []} onCite={onCite} />
      {brief.sections.map((section) => (
        <article key={section.title} className="brief-section">
          <h3>{section.title}</h3>
          {uniqueBy(section.sentences, (s) => s.text.trim()).map((sentence) => {
            const hit = sentence.cites.some(isMatch);
            return (
              <p key={sentence.text} className={hit ? "is-match" : undefined}>
                {sentence.text}{" "}
                {uniqueBy(sentence.cites, (c) => c.label || c.id).map((cite) => (
                  <CiteButton key={cite.id} cite={cite} match={isMatch(cite)} onCite={onCite} />
                ))}
              </p>
            );
          })}
        </article>
      ))}
      {brief.limitations.length > 0 ? (
        <article className="brief-section">
          <h3>Limitations</h3>
          <ul className="compact-list">
            {brief.limitations.map((line) => (
              <li key={line}>{line}</li>
            ))}
          </ul>
        </article>
      ) : null}
    </div>
  );
}
