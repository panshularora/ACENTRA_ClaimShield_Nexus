import type { TimelineEvent } from "../../api/types";

export function TimelinePanel({
  events,
  loading,
  error,
  onOpen,
}: {
  events: TimelineEvent[] | undefined;
  loading: boolean;
  error: string | null;
  onOpen: (ref: string) => void;
}) {
  const rows = events ?? [];
  return (
    <section className="ws-panel ws-timeline" aria-labelledby="tl-title">
      <header className="ws-panel-head">
        <p className="kicker">Panel 4</p>
        <h2 id="tl-title">Timeline</h2>
      </header>
      {loading && <p className="muted">Loading chronology…</p>}
      {error && <p className="error-text">{error}</p>}
      {!loading && rows.length === 0 && <p className="empty">No dated evidence on this case.</p>}
      <ol className="tl">
        {rows.map((ev) => (
          <li key={`${ev.ref}-${ev.ts}`} className={ev.flag ? "flagged" : ""}>
            <button type="button" className="tl-item" onClick={() => onOpen(ev.ref)}>
              <time className="mono">{ev.ts}</time>
              <span className={`tl-kind kind-${ev.kind}`}>{ev.kind}</span>
              <strong>{ev.title}</strong>
              <span className="muted">{ev.detail}</span>
            </button>
          </li>
        ))}
      </ol>
    </section>
  );
}
