import { useQuery } from "@tanstack/react-query";
import { Link } from "@tanstack/react-router";
import { useEffect, useMemo, useState } from "react";
import { api, can } from "../../api/client";
import type { HistoryItem, HistoryKind } from "../../api/types";
import { useAuth } from "../../auth/AuthProvider";
import { StatusBadge } from "../../components/Badge";
import { Panel } from "../../components/ui/Panel";
import { EmptyState, ErrorState, LoadingState } from "../../components/ui/States";
import { money } from "../../lib/format";

type Filter = "all" | HistoryKind;

/** Desk history is paged so a long extract does not dump every prior case at once. */
const PAGE_SIZE = 10;

const FILTER_LABEL: Record<Filter, string> = {
  all: "All",
  case: "SIU cases",
  investigation: "Prior investigations",
};

function when(item: HistoryItem): string {
  return item.closed_at || item.opened_at || "—";
}

function dollars(item: HistoryItem): string {
  const value = item.kind === "investigation" ? item.amount_identified : item.flagged_dollars;
  return value == null ? "—" : money(value);
}

interface HistoryPanelProps {
  title?: string;
  description?: string;
  compact?: boolean;
}

/** Decided SIU cases, earlier-run cases, and extract investigations. */
export function HistoryPanel({
  title = "History",
  description = "Closed work, earlier runs, and prior SIU investigations. Outcomes are substantiated, education, referred, or unsubstantiated.",
  compact = false,
}: HistoryPanelProps) {
  const { user } = useAuth();
  const canRead = can(user, "case:read");
  const [filter, setFilter] = useState<Filter>("all");
  const [queryText, setQueryText] = useState("");
  const [page, setPage] = useState(0);

  const historyQuery = useQuery({
    queryKey: ["case-history"],
    queryFn: api.getCaseHistory,
    enabled: canRead,
  });

  const items = historyQuery.data?.items ?? [];
  const visible = useMemo(() => {
    const q = queryText.trim().toLowerCase();
    return items.filter((row) => {
      if (filter !== "all" && row.kind !== filter) return false;
      if (!q) return true;
      return [
        row.id,
        row.case_id ?? "",
        row.provider_name,
        row.provider_id ?? "",
        row.npi ?? "",
        row.outcome_label,
        row.status,
        row.scheme_tag ?? "",
      ].some((value) => value.toLowerCase().includes(q));
    });
  }, [items, filter, queryText]);

  useEffect(() => {
    setPage(0);
  }, [filter, queryText]);

  const pageCount = Math.max(1, Math.ceil(visible.length / PAGE_SIZE));
  const safePage = Math.min(page, pageCount - 1);
  const pageItems = visible.slice(safePage * PAGE_SIZE, safePage * PAGE_SIZE + PAGE_SIZE);
  const from = visible.length === 0 ? 0 : safePage * PAGE_SIZE + 1;
  const to = Math.min(visible.length, safePage * PAGE_SIZE + pageItems.length);

  const counts = {
    all: items.length,
    case: items.filter((row) => row.kind === "case").length,
    investigation: items.filter((row) => row.kind === "investigation").length,
  };

  if (!canRead) return null;

  return (
    <Panel
      id="case-history"
      eyebrow="History"
      title={title}
      description={description}
      actions={
        <span className="badge">
          {visible.length === 0 ? "0 rows" : `${from}–${to} of ${visible.length}`}
        </span>
      }
    >
      {historyQuery.error ? <ErrorState title="History could not be loaded" error={historyQuery.error} /> : null}
      <div className="toolbar">
        <div className="segmented" role="group" aria-label="History source">
          {(Object.keys(FILTER_LABEL) as Filter[]).map((key) => (
            <button key={key} type="button" aria-pressed={filter === key} onClick={() => setFilter(key)}>
              {FILTER_LABEL[key]} <span className="count">{counts[key]}</span>
            </button>
          ))}
        </div>
        <label className="field grow">
          Search
          <input
            type="search"
            placeholder="Provider, NPI, outcome, case…"
            value={queryText}
            onChange={(event) => setQueryText(event.target.value)}
          />
        </label>
      </div>
      {historyQuery.isLoading ? <LoadingState label="Loading history…" /> : null}
      {!historyQuery.isLoading && visible.length === 0 ? (
        <EmptyState title="No history in this view" compact>
          Load a batch to see prior investigations. Decided SIU cases appear after a monitor, dismiss, or referral.
        </EmptyState>
      ) : null}
      {visible.length > 0 ? (
        <ul className={compact ? "history-list compact" : "history-list"}>
          {pageItems.map((row) => (
            <li key={`${row.kind}-${row.id}`} className={`history-row kind-${row.kind}`}>
              <div className="history-main">
                {row.case_id ? (
                  <Link to="/investigator/workspace/$caseId" params={{ caseId: row.case_id }} className="work-card-name">
                    {row.provider_name}
                  </Link>
                ) : (
                  <strong className="work-card-name">{row.provider_name}</strong>
                )}
                <p className="work-card-meta">
                  <span className="mono">{row.id}</span>
                  {row.npi ? <span className="mono">NPI {row.npi}</span> : null}
                  {row.specialty ? <span>{row.specialty.replaceAll("_", " ")}</span> : null}
                  {row.scheme_tag ? <span>{row.scheme_tag}</span> : null}
                  {row.kind === "investigation" ? <span>Prior investigation</span> : <span>SIU case</span>}
                  {row.current_run ? <span>This run</span> : null}
                </p>
                {row.reason ? <p className="muted history-reason">{row.reason}</p> : null}
              </div>
              <div className="history-side">
                <StatusBadge status={row.outcome_label} />
                <span className="history-dollars">{dollars(row)}</span>
                <time className="muted" dateTime={when(row)}>
                  {when(row)}
                </time>
              </div>
            </li>
          ))}
        </ul>
      ) : null}
      {visible.length > PAGE_SIZE ? (
        <nav className="history-pager" aria-label="History pages">
          <button type="button" className="btn" disabled={safePage === 0} onClick={() => setPage(safePage - 1)}>
            Previous
          </button>
          <p className="history-pager-status">
            Page {safePage + 1} of {pageCount}
          </p>
          <button
            type="button"
            className="btn"
            disabled={safePage >= pageCount - 1}
            onClick={() => setPage(safePage + 1)}
          >
            Next
          </button>
        </nav>
      ) : null}
      {historyQuery.data?.note ? <p className="field-hint">{historyQuery.data.note}</p> : null}
    </Panel>
  );
}
