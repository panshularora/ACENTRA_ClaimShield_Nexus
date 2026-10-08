import { useMemo, useState } from "react";
import type { ClaimRow, ClaimsPack } from "../../api/types";
import { EmptyState, ErrorState, LoadingState } from "../../components/ui/States";
import { money, neutralLabel } from "../../lib/format";

type SortKey = "dos" | "paid" | "code" | "provider" | "member";
type SortDir = "ascending" | "descending";

const SORTABLE: { key: SortKey; label: string; numeric?: boolean }[] = [
  { key: "dos", label: "DOS" },
  { key: "code", label: "Code" },
  { key: "paid", label: "Paid", numeric: true },
  { key: "provider", label: "Rendering" },
  { key: "member", label: "Member" },
];

function compareRows(a: ClaimRow, b: ClaimRow, key: SortKey): number {
  if (key === "paid") return a.paid - b.paid;
  if (key === "code") return a.code.localeCompare(b.code);
  if (key === "provider") return a.rendering_provider_id.localeCompare(b.rendering_provider_id);
  if (key === "member") return a.member.display.localeCompare(b.member.display);
  return (a.dos_from ?? "").localeCompare(b.dos_from ?? "") || a.line_id.localeCompare(b.line_id);
}

function matchesQuery(row: ClaimRow, q: string): boolean {
  return [
    row.line_id,
    row.claim_id,
    row.code,
    row.rendering_provider_id,
    row.billing_provider_id ?? "",
    row.member.display,
    row.facility_id ?? "",
  ].some((value) => value.toLowerCase().includes(q));
}

interface ClaimsTableProps {
  pack: ClaimsPack | undefined;
  loading: boolean;
  error: unknown;
  onOpenLine: (lineId: string) => void;
  /** Line ids for the focused network entity, or null when nothing is focused. */
  focusLineIds: Set<string> | null;
  focusLabel: string | null;
  onClearFocus: () => void;
}

export function ClaimsTable({ pack, loading, error, onOpenLine, focusLineIds, focusLabel, onClearFocus }: ClaimsTableProps) {
  const [query, setQuery] = useState("");
  const [signal, setSignal] = useState("all");
  const [sort, setSort] = useState<{ key: SortKey; dir: SortDir }>({ key: "dos", dir: "ascending" });

  const rows = useMemo(() => pack?.rows ?? [], [pack]);
  const signals = useMemo(
    () => [...new Set(rows.flatMap((row) => row.signals.map((s) => s.rule_id).filter((id): id is string => Boolean(id))))],
    [rows],
  );

  const visible = useMemo(() => {
    const q = query.trim().toLowerCase();
    const filtered = rows.filter(
      (row) =>
        (!focusLineIds || focusLineIds.has(row.line_id)) &&
        (signal === "all" || row.signals.some((s) => s.rule_id === signal)) &&
        (!q || matchesQuery(row, q)),
    );
    const sign = sort.dir === "ascending" ? 1 : -1;
    return filtered.sort((a, b) => sign * compareRows(a, b, sort.key));
  }, [rows, query, signal, sort, focusLineIds]);

  const totalPaid = visible.reduce((sum, row) => sum + row.paid, 0);

  if (loading) return <LoadingState label="Loading flagged claim lines…" />;
  if (error) return <ErrorState title="Claims unavailable" error={error} />;

  return (
    <div className="claims">
      <div className="section-subhead">
        <h3 id="claims-table-title">Claim lines</h3>
        <span className="muted">
          {visible.length} of {rows.length} lines · {money(totalPaid)} paid
        </span>
      </div>
      {focusLineIds ? (
        <p className="banner ok focus-banner">
          Showing lines that involve <strong>{focusLabel}</strong>.{" "}
          <button type="button" className="link-button" onClick={onClearFocus}>
            Show all lines
          </button>
        </p>
      ) : null}
      {pack?.masked ? <p className="note">Member names are masked; IDs only, per role-based access.</p> : null}
      <div className="toolbar">
        <label className="field grow">
          Filter
          <input
            type="search"
            placeholder="Line, claim, code, provider, member…"
            value={query}
            onChange={(event) => setQuery(event.target.value)}
          />
        </label>
        <label className="field">
          Signal
          <select value={signal} onChange={(event) => setSignal(event.target.value)}>
            <option value="all">All signals</option>
            {signals.map((id) => (
              <option key={id} value={id}>
                {id}
              </option>
            ))}
          </select>
        </label>
      </div>
      {visible.length === 0 ? (
        <EmptyState title="No matching claim lines" compact>
          {rows.length === 0 ? "This case has no flagged claim lines." : "Change the filters to see more lines."}
        </EmptyState>
      ) : (
        <div className="table-wrap claims-wrap">
          <table className="grid" aria-labelledby="claims-table-title">
            <thead>
              <tr>
                {SORTABLE.slice(0, 1).map((col) => (
                  <SortHeader key={col.key} col={col} sort={sort} onSort={setSort} />
                ))}
                <th scope="col">Line</th>
                {SORTABLE.slice(1, 3).map((col) => (
                  <SortHeader key={col.key} col={col} sort={sort} onSort={setSort} />
                ))}
                <th scope="col" className="num">
                  Units
                </th>
                <SortHeader col={SORTABLE[3]} sort={sort} onSort={setSort} />
                <th scope="col">Billing</th>
                <SortHeader col={SORTABLE[4]} sort={sort} onSort={setSort} />
                <th scope="col">Facility</th>
                <th scope="col">Source</th>
                <th scope="col">Signals</th>
              </tr>
            </thead>
            <tbody>
              {visible.map((row) => (
                <tr key={row.line_id}>
                  <td className="mono">{row.dos_from ?? "—"}</td>
                  <td>
                    <button type="button" className="link-button mono" onClick={() => onOpenLine(row.line_id)}>
                      {row.line_id}
                    </button>
                  </td>
                  <td className="mono">
                    {row.code} <span className="muted">{row.code_system}</span>
                  </td>
                  <td className="num dollars">{money(row.paid)}</td>
                  <td className="num">{row.units}</td>
                  <td className="mono">{row.rendering_provider_id}</td>
                  <td className="mono">{row.billing_provider_id ?? "—"}</td>
                  <td>{row.member.display}</td>
                  <td className="mono">{row.facility_id ?? "—"}</td>
                  <td className="mono muted">
                    {row.source_system ?? "—"}
                    {row.received_date ? ` · rcvd ${row.received_date}` : ""}
                  </td>
                  <td>
                    <span className="chip-row">
                      {row.signals.length === 0
                        ? "—"
                        : row.signals.map((s) => (
                            <span key={s.alert_id} className="badge" title={neutralLabel(s.label)}>
                              {s.rule_id ?? neutralLabel(s.label)}
                            </span>
                          ))}
                    </span>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
    </div>
  );
}

function SortHeader({
  col,
  sort,
  onSort,
}: {
  col: { key: SortKey; label: string; numeric?: boolean };
  sort: { key: SortKey; dir: SortDir };
  onSort: (next: { key: SortKey; dir: SortDir }) => void;
}) {
  const active = sort.key === col.key;
  return (
    <th scope="col" className={col.numeric ? "num" : undefined} aria-sort={active ? sort.dir : undefined}>
      <button
        type="button"
        className="sort-button"
        onClick={() => onSort({ key: col.key, dir: active && sort.dir === "ascending" ? "descending" : "ascending" })}
      >
        {col.label}
        <span aria-hidden="true">{active ? (sort.dir === "ascending" ? " ▲" : " ▼") : ""}</span>
      </button>
    </th>
  );
}
