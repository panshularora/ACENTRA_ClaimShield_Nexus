import { useMemo, useState } from "react";
import type { ClaimRow, ClaimsPack } from "../../api/types";
import { money } from "../../lib/format";

type SortKey = "dos" | "paid" | "code" | "provider" | "member";

export function ClaimsTable({
  pack,
  loading,
  error,
  onOpenLine,
}: {
  pack: ClaimsPack | undefined;
  loading: boolean;
  error: string | null;
  onOpenLine: (lineId: string) => void;
}) {
  const [query, setQuery] = useState("");
  const [signal, setSignal] = useState("all");
  const [sortKey, setSortKey] = useState<SortKey>("dos");

  const rows = pack?.rows ?? [];
  const signals = useMemo(() => {
    const set = new Set<string>();
    for (const row of rows) {
      for (const s of row.signals) {
        if (s.rule_id) set.add(s.rule_id);
      }
    }
    return [...set];
  }, [rows]);

  const visible = useMemo(() => {
    const q = query.trim().toLowerCase();
    const filtered = rows.filter((row) => {
      if (signal !== "all" && !row.signals.some((s) => s.rule_id === signal)) return false;
      if (!q) return true;
      return (
        row.line_id.toLowerCase().includes(q) ||
        row.claim_id.toLowerCase().includes(q) ||
        row.code.toLowerCase().includes(q) ||
        row.rendering_provider_id.toLowerCase().includes(q) ||
        (row.billing_provider_id ?? "").toLowerCase().includes(q) ||
        row.member.display.toLowerCase().includes(q) ||
        (row.facility_id ?? "").toLowerCase().includes(q)
      );
    });
    filtered.sort((a, b) => compareRows(a, b, sortKey));
    return filtered;
  }, [rows, query, signal, sortKey]);

  return (
    <section className="ws-panel ws-claims" aria-labelledby="claims-title">
      <header className="ws-panel-head">
        <div>
          <p className="kicker">Claims</p>
          <h2 id="claims-title">Claim lines</h2>
        </div>
        <span className="muted mono">{visible.length} lines</span>
      </header>
      {pack?.masked && (
        <p className="note">Member names are masked. IDs only, per RBAC.</p>
      )}
      <div className="toolbar tight">
        <label className="grow">
          <span className="sr">Filter claims</span>
          <input
            type="search"
            placeholder="Filter line, code, provider, member…"
            value={query}
            onChange={(e) => setQuery(e.target.value)}
          />
        </label>
        <label>
          <span className="sr">Signal</span>
          <select value={signal} onChange={(e) => setSignal(e.target.value)} aria-label="Signal">
            <option value="all">All signals</option>
            {signals.map((id) => (
              <option key={id} value={id}>
                {id}
              </option>
            ))}
          </select>
        </label>
        <label>
          <span className="sr">Sort</span>
          <select value={sortKey} onChange={(e) => setSortKey(e.target.value as SortKey)} aria-label="Sort">
            <option value="dos">Date of service</option>
            <option value="paid">Paid</option>
            <option value="code">Code</option>
            <option value="provider">Rendering provider</option>
            <option value="member">Member</option>
          </select>
        </label>
      </div>
      {loading && <p className="muted">Loading flagged claim lines…</p>}
      {error && <p className="error-text">{error}</p>}
      {!loading && visible.length === 0 && <p className="empty">No flagged claim lines on this case.</p>}
      {visible.length > 0 && (
        <div className="table-wrap claims-wrap">
          <table className="grid">
            <thead>
              <tr>
                <th>DOS</th>
                <th>Line</th>
                <th>Code</th>
                <th>Paid</th>
                <th>Units</th>
                <th>Rendering</th>
                <th>Billing</th>
                <th>Member</th>
                <th>Facility</th>
                <th>Signals</th>
              </tr>
            </thead>
            <tbody>
              {visible.map((row) => (
                <tr
                  key={row.line_id}
                  tabIndex={0}
                  onClick={() => onOpenLine(row.line_id)}
                  onKeyDown={(e) => {
                    if (e.key === "Enter" || e.key === " ") {
                      e.preventDefault();
                      onOpenLine(row.line_id);
                    }
                  }}
                >
                  <td className="mono">{row.dos_from ?? "—"}</td>
                  <td className="mono">{row.line_id}</td>
                  <td className="mono">
                    {row.code}
                    <span className="muted"> {row.code_system}</span>
                  </td>
                  <td className="mono dollars">{money(row.paid)}</td>
                  <td className="mono">{row.units}</td>
                  <td className="mono">{row.rendering_provider_id}</td>
                  <td className="mono">{row.billing_provider_id ?? "—"}</td>
                  <td>{row.member.display}</td>
                  <td className="mono">{row.facility_id ?? "—"}</td>
                  <td>
                    {row.signals.length === 0
                      ? "—"
                      : row.signals.map((s) => s.rule_id ?? s.label).join(", ")}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
    </section>
  );
}

function compareRows(a: ClaimRow, b: ClaimRow, key: SortKey): number {
  if (key === "paid") return b.paid - a.paid;
  if (key === "code") return a.code.localeCompare(b.code);
  if (key === "provider") return a.rendering_provider_id.localeCompare(b.rendering_provider_id);
  if (key === "member") return a.member.display.localeCompare(b.member.display);
  return (a.dos_from ?? "").localeCompare(b.dos_from ?? "") || a.line_id.localeCompare(b.line_id);
}
