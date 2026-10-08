import type { ClaimRow, TimelineEvent } from "../../api/types";
import { ClaimsTimelineChart } from "../../components/charts/ClaimsTimelineChart";
import { EmptyState, ErrorState, LoadingState } from "../../components/ui/States";
import { humanize } from "../../lib/format";

interface TimelinePanelProps {
  rows: ClaimRow[] | undefined;
  events: TimelineEvent[] | undefined;
  subjectId: string;
  loading: boolean;
  error: unknown;
  onOpen: (ref: string) => void;
}

const OPENABLE = ["line:", "alert:", "claim:", "provider:"];

/** Time-axis chart of flagged claims with event markers, plus the full chronology list. */
export function TimelinePanel({ rows, events, subjectId, loading, error, onOpen }: TimelinePanelProps) {
  if (loading) return <LoadingState label="Loading claims and chronology…" />;
  if (error) return <ErrorState title="Timeline unavailable" error={error} />;
  const claimRows = rows ?? [];
  const chronology = events ?? [];
  if (claimRows.length === 0 && chronology.length === 0) {
    return <EmptyState title="No dated evidence">The API returned no dated claim lines or events for this case.</EmptyState>;
  }
  return (
    <div className="timeline">
      {claimRows.some((row) => row.dos_from) ? (
        <ClaimsTimelineChart rows={claimRows} events={chronology} subjectId={subjectId} />
      ) : (
        <EmptyState title="No dated claim lines" compact>
          Claim lines on this case have no date of service, so the time chart cannot be drawn.
        </EmptyState>
      )}
      {chronology.length > 0 ? (
        <details className="chronology">
          <summary>
            Full chronology <span className="muted">({chronology.length} events)</span>
          </summary>
          <ol className="tl">
            {chronology.map((event) => {
              const openable = OPENABLE.some((prefix) => event.ref.startsWith(prefix));
              return (
                <li key={`${event.ref}-${event.ts}`} className={event.flag ? "is-flagged" : undefined}>
                  <time className="mono" dateTime={event.ts}>
                    {event.ts}
                  </time>
                  <span className="badge">{humanize(event.kind)}</span>
                  {openable ? (
                    <button type="button" className="link-button" onClick={() => onOpen(event.ref)}>
                      {event.title}
                    </button>
                  ) : (
                    <strong>{event.title}</strong>
                  )}
                  <span className="muted">{event.detail}</span>
                  {event.flag ? <span className="badge tone-danger">Flagged</span> : null}
                </li>
              );
            })}
          </ol>
        </details>
      ) : null}
    </div>
  );
}
