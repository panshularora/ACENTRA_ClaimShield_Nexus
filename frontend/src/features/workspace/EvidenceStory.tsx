// Plain-language finding story plus a folded technical section for the same evidence packet.
import type { ReactNode } from "react";
import type { AlertLineage, CaseAlert } from "../../api/types";
import { alertLabel, pct } from "../../lib/format";
import { fieldPlain, findingCopy, sourcePlain } from "../../lib/plainLanguage";

export const APPROACH_PLAIN: Record<string, { label: string; tech: string }> = {
  hard_rule: { label: "Claim check", tech: "hard_rule · catalog rule on paid lines" },
  rules: { label: "Claim check", tech: "hard_rule · catalog rule on paid lines" },
  behavioral_anomaly: {
    label: "Compared with similar providers",
    tech: "behavioral_anomaly · like-with-like peer residual",
  },
  anomaly: {
    label: "Compared with similar providers",
    tech: "behavioral_anomaly · like-with-like peer residual",
  },
  network_graph: {
    label: "Linked providers",
    tech: "network_graph · shared owner / TIN / contact / referral",
  },
  graph: {
    label: "Linked providers",
    tech: "network_graph · shared owner / TIN / contact / referral",
  },
};

function isRecord(value: unknown): value is Record<string, unknown> {
  return typeof value === "object" && value !== null;
}

function str(value: unknown): string | null {
  return typeof value === "string" && value ? value : null;
}

function num(value: unknown): number | null {
  return typeof value === "number" && Number.isFinite(value) ? value : null;
}

/** Concrete numbers already on the alert, labeled in SIU English. */
export function evidenceHighlights(evidence?: Record<string, unknown>): { label: string; value: string }[] {
  if (!evidence) return [];
  const rows: { label: string; value: string }[] = [];
  const dod = str(evidence.dod);
  if (dod) rows.push({ label: "Date of death on file", value: dod });
  const nLines = num(evidence.n_lines);
  if (nLines != null) rows.push({ label: "Lines in this hit", value: String(nLines) });
  const members = Array.isArray(evidence.member_ids) ? evidence.member_ids.length : 0;
  if (members > 0) rows.push({ label: "Members on this hit", value: String(members) });
  const z = num(evidence.robust_z);
  if (z != null) rows.push({ label: "Distance from similar providers (robust z)", value: z.toFixed(2) });
  const nPeers = num(evidence.n_peers) ?? (isRecord(evidence.peer_group) ? num(evidence.peer_group.n_peers) : null);
  if (nPeers != null) rows.push({ label: "Similar providers in the comparison", value: String(nPeers) });
  const median = num(evidence.peer_median);
  if (median != null) rows.push({ label: "Typical value for similar providers", value: String(median) });
  const share = num(evidence.share) ?? num(evidence.referral_share);
  if (share != null) rows.push({ label: "Share of referrals to one receiver", value: pct(share) });
  const bypass = Array.isArray(evidence.bypass_checked)
    ? evidence.bypass_checked.filter((item): item is string => typeof item === "string")
    : [];
  if (bypass.length) rows.push({ label: "Bypass codes checked", value: bypass.join(", ") });
  const policy = str(evidence.policy_ref);
  if (policy) rows.push({ label: "Policy reference", value: policy });
  return rows;
}

export function SourceList({
  tables,
  compact,
}: {
  tables?: { table: string; role: string }[];
  compact?: boolean;
}) {
  if (!tables || tables.length === 0) return null;
  return (
    <ul className={`source-list${compact ? " compact" : ""}`}>
      {tables.map((src) => (
        <li key={src.table}>
          <span className="mono">{src.table}</span>
          <span>{sourcePlain(src.table, src.role)}</span>
        </li>
      ))}
    </ul>
  );
}

interface EvidenceStoryProps {
  kind?: string;
  fallbackTitle?: string;
  lineage?: AlertLineage | null;
  evidence?: Record<string, unknown>;
  lineIds?: string[];
  ruleId?: string | null;
  ruleVersion?: number | null;
  policyRef?: string | null;
  detector?: string;
  approach?: string;
  score?: number;
  peer?: ReactNode;
}

/** Plain-language packet plus a technical fold. Used on finding cards and in the drawer. */
export function EvidenceStory({
  kind,
  fallbackTitle,
  lineage,
  evidence,
  lineIds,
  ruleId,
  ruleVersion,
  policyRef,
  detector,
  approach,
  score,
  peer,
}: EvidenceStoryProps) {
  const copy = findingCopy(kind, fallbackTitle ?? "Pattern");
  const approachKey = approach ?? detector ?? "";
  const approachCopy = APPROACH_PLAIN[approachKey] ?? {
    label: "Paid-claim check",
    tech: detector ?? "detector",
  };
  const highlights = evidenceHighlights(evidence);
  const lineCount = lineIds?.length ?? 0;
  const fields = lineage?.fields_used?.filter(Boolean) ?? [];
  const version = ruleVersion != null ? ` v${ruleVersion}` : "";

  return (
    <div className="ev-story">
      <p className="ev-what">{copy.what}</p>
      <p>
        <strong>What to check.</strong> {copy.check}
      </p>
      {lineCount > 0 ? (
        <p>
          {lineCount} paid claim line{lineCount === 1 ? "" : "s"} sit{lineCount === 1 ? "s" : ""} under this
          pattern.
        </p>
      ) : null}
      {highlights.length > 0 ? (
        <dl className="facts dense">
          {highlights.map((row) => (
            <div key={row.label}>
              <dt>{row.label}</dt>
              <dd>{row.value}</dd>
            </div>
          ))}
        </dl>
      ) : null}
      {peer}
      <details className="ev-tech">
        <summary>Technical — how this was produced</summary>
        <p>{lineage?.method ?? `${copy.source}. A person still has to review it.`}</p>
        {lineage?.how ? <p>{lineage.how}</p> : null}
        <dl className="facts dense">
          <div>
            <dt>Approach</dt>
            <dd className="mono">{approachCopy.tech}</dd>
          </div>
          {detector ? (
            <div>
              <dt>Detector</dt>
              <dd className="mono">{detector}</dd>
            </div>
          ) : null}
          {ruleId ? (
            <div>
              <dt>Rule</dt>
              <dd className="mono">
                {ruleId}
                {version}
              </dd>
            </div>
          ) : null}
          {policyRef ? (
            <div>
              <dt>Policy ref</dt>
              <dd className="mono">{policyRef}</dd>
            </div>
          ) : null}
          {kind ? (
            <div>
              <dt>Kind</dt>
              <dd className="mono">{kind}</dd>
            </div>
          ) : null}
          {score != null ? (
            <div>
              <dt>Detector score</dt>
              <dd>{pct(score)}</dd>
            </div>
          ) : null}
          {fields.length > 0 ? (
            <div>
              <dt>Fields used</dt>
              <dd>{fields.map(fieldPlain).join(", ")}</dd>
            </div>
          ) : null}
        </dl>
        {lineage?.tables && lineage.tables.length > 0 ? (
          <>
            <h4>Tables used</h4>
            <SourceList tables={lineage.tables} />
          </>
        ) : (
          <p className="muted">Source: {copy.source}.</p>
        )}
      </details>
    </div>
  );
}

export function storyFromAlert(alert: CaseAlert) {
  const kind = typeof alert.evidence?.kind === "string" ? alert.evidence.kind : alert.kind;
  return {
    kind,
    fallbackTitle: alertLabel(alert),
    lineage: alert.lineage,
    evidence: alert.evidence,
    lineIds: alert.line_ids,
    ruleId: alert.rule_id,
    ruleVersion: alert.rule_version,
    policyRef: alert.policy_ref,
    detector: alert.detector,
    approach: alert.approach,
    score: alert.score,
  };
}
