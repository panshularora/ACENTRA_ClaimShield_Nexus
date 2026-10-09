// Finding packet: the problem, where it sits, why it fired, then a short "how we checked".
import type { ReactNode } from "react";
import type { AlertLineage, CaseAlert } from "../../api/types";
import { alertLabel, money, pct } from "../../lib/format";
import { findingCopy, sourcePlain } from "../../lib/plainLanguage";

export const APPROACH_PLAIN: Record<string, { label: string; tech: string }> = {
  hard_rule: { label: "Claim check", tech: "A catalog rule on paid lines" },
  rules: { label: "Claim check", tech: "A catalog rule on paid lines" },
  behavioral_anomaly: {
    label: "Peer compare",
    tech: "Compared with similar providers",
  },
  anomaly: {
    label: "Peer compare",
    tech: "Compared with similar providers",
  },
  network_graph: {
    label: "Linked providers",
    tech: "Shared owner, tax ID, contact, or referral",
  },
  graph: {
    label: "Linked providers",
    tech: "Shared owner, tax ID, contact, or referral",
  },
};

const EDGE_PLAIN: Record<string, string> = {
  tin: "shared tax ID",
  shared_tin: "shared tax ID",
  owner: "shared owner",
  shared_owner: "shared owner",
  ownership: "shared owner",
  contact: "shared phone, email, or bank details",
  shared_contact: "shared phone, email, or bank details",
  referral: "referral",
  location: "shared address",
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

function strList(value: unknown): string[] {
  if (!Array.isArray(value)) return [];
  return value.filter((item): item is string => typeof item === "string" && item.length > 0);
}

function previewIds(ids: string[]): string {
  if (ids.length <= 3) return ids.join(", ");
  return `${ids.slice(0, 3).join(", ")} +${ids.length - 3} more`;
}

function looksHuman(value: string): boolean {
  return value.length < 90 && !value.includes("_") && /[A-Za-z]/.test(value) && !/^[A-Z]-/.test(value);
}

function distancePlain(z: number): string {
  const mag = Math.abs(z);
  if (mag >= 4) return "Far outside similar providers";
  if (mag >= 3) return "Well above similar providers";
  if (mag >= 2) return "Above similar providers";
  return "Slightly above similar providers";
}

function linkKinds(value: unknown): string | null {
  const raw = strList(value);
  if (!raw.length) return null;
  return raw
    .map((kind) => {
      const key = kind.toLowerCase().replaceAll(" ", "_");
      return EDGE_PLAIN[key] ?? EDGE_PLAIN[key.replace(/^shared_/, "")] ?? kind.replaceAll("_", " ");
    })
    .join(", ");
}

/** Where the hit lives — lines, people, dates, dollars. */
export function evidenceWhere(
  evidence?: Record<string, unknown>,
  lineIds?: string[],
): { label: string; value: string }[] {
  if (!evidence && (!lineIds || lineIds.length === 0)) return [];
  const rows: { label: string; value: string }[] = [];
  const lines = lineIds && lineIds.length > 0 ? lineIds : strList(evidence?.line_ids);
  if (lines.length) rows.push({ label: "Claim lines", value: `${lines.length} cited · ${previewIds(lines)}` });
  const members = strList(evidence?.member_ids);
  const oneMember = str(evidence?.member_id);
  if (members.length) rows.push({ label: "Members", value: `${members.length} on this hit` });
  else if (oneMember) rows.push({ label: "Member", value: oneMember });
  const nProviders = num(evidence?.n_providers);
  const peers = strList(evidence?.peer_ids);
  if (nProviders != null) rows.push({ label: "Providers in this group", value: String(nProviders) });
  else if (peers.length) rows.push({ label: "Linked providers", value: String(peers.length) });
  const dod = str(evidence?.dod);
  if (dod) rows.push({ label: "Date of death on file", value: dod });
  const dos = str(evidence?.dos_from) ?? str(evidence?.dos) ?? str(evidence?.date_of_service);
  if (dos) rows.push({ label: "Service date", value: dos });
  const code = str(evidence?.code);
  const codes = strList(evidence?.codes);
  const col1 = str(evidence?.column1);
  const col2 = str(evidence?.column2);
  if (code) rows.push({ label: "Service code", value: code });
  else if (codes.length) rows.push({ label: "Service codes", value: previewIds(codes) });
  else if (col1 && col2) rows.push({ label: "Code pair", value: `${col1} with ${col2}` });
  const paid = num(evidence?.paid) ?? num(evidence?.flagged_dollars) ?? num(evidence?.amount);
  if (paid != null) rows.push({ label: "Paid on these lines", value: money(paid) });
  const npi = str(evidence?.npi) ?? str(evidence?.billing_npi);
  if (npi) rows.push({ label: "NPI", value: npi });
  const owner = str(evidence?.owner_name);
  if (owner) rows.push({ label: "Owner on file", value: owner });
  const excl = str(evidence?.excl_date);
  if (excl) rows.push({ label: "Exclusion date", value: excl });
  return rows;
}

/** Extra numbers that explain why the check fired, in SIU English. */
export function evidenceWhy(evidence?: Record<string, unknown>): { label: string; value: string }[] {
  if (!evidence) return [];
  const rows: { label: string; value: string }[] = [];
  const metric = str(evidence.metric);
  if (metric) rows.push({ label: "What we compared", value: metric });
  const z = num(evidence.robust_z);
  if (z != null) rows.push({ label: "How unusual", value: distancePlain(z) });
  const providerValue = num(evidence.provider_value);
  if (providerValue != null) {
    rows.push({
      label: "This provider",
      value: Number.isInteger(providerValue) ? String(providerValue) : providerValue.toFixed(2),
    });
  }
  const nPeers = num(evidence.n_peers) ?? (isRecord(evidence.peer_group) ? num(evidence.peer_group.n_peers) : null);
  if (nPeers != null) rows.push({ label: "Similar providers compared", value: String(nPeers) });
  const median = num(evidence.peer_median);
  if (median != null) rows.push({ label: "Typical similar-provider value", value: String(median) });
  const fence = num(evidence.fence);
  if (fence != null) rows.push({ label: "Usual upper range", value: String(fence) });
  const share = num(evidence.share) ?? num(evidence.referral_share) ?? num(evidence.top_share);
  if (share != null) rows.push({ label: "Share going to one receiver", value: pct(share) });
  const nRefs = num(evidence.n_referrals);
  if (nRefs != null) rows.push({ label: "Referrals in the window", value: String(nRefs) });
  const minutes = num(evidence.minutes);
  const maxMinutes = num(evidence.max_minutes);
  if (minutes != null && maxMinutes != null) {
    rows.push({ label: "Minutes billed that day", value: `${minutes} (usual cap ${maxMinutes})` });
  } else if (minutes != null) {
    rows.push({ label: "Minutes billed that day", value: String(minutes) });
  }
  const nLines = num(evidence.n_lines);
  if (nLines != null) rows.push({ label: "Lines in this hit", value: String(nLines) });
  const nClaims = num(evidence.n_claims);
  if (nClaims != null) rows.push({ label: "Claims in this group", value: String(nClaims) });
  const links = linkKinds(evidence.edge_kinds);
  if (links) rows.push({ label: "How the NPIs are linked", value: links });
  return rows;
}

export function whereSummary(evidence?: Record<string, unknown>, lineIds?: string[]): string {
  const parts: string[] = [];
  const n = lineIds?.length ?? strList(evidence?.line_ids).length;
  if (n) parts.push(`${n} claim line${n === 1 ? "" : "s"}`);
  const members = strList(evidence?.member_ids).length;
  if (members) parts.push(`${members} member${members === 1 ? "" : "s"}`);
  const nProviders = num(evidence?.n_providers);
  if (nProviders != null) parts.push(`${nProviders} linked provider${nProviders === 1 ? "" : "s"}`);
  const dod = str(evidence?.dod);
  if (dod) parts.push(`death date ${dod}`);
  const dos = str(evidence?.dos_from) ?? str(evidence?.dos);
  if (dos) parts.push(`service ${dos}`);
  const excl = str(evidence?.excl_date);
  if (excl) parts.push(`exclusion ${excl}`);
  return parts.join(" · ");
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
        <li key={src.table}>{sourcePlain(src.table, src.role)}</li>
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
  ruleTitle?: string | null;
  ruleVersion?: number | null;
  policyRef?: string | null;
  detector?: string;
  approach?: string;
  score?: number;
  reviewReason?: string | null;
  peer?: ReactNode;
}

function howWeChecked(args: {
  copySource: string;
  approachLabel: string;
  lineage?: AlertLineage | null;
  ruleTitle?: string | null;
}): string[] {
  const bullets: string[] = [];
  bullets.push(`Looked at: ${args.copySource.toLowerCase()}.`);
  bullets.push(`The test: ${args.approachLabel.toLowerCase()}.`);
  if (args.lineage?.how && args.lineage.how.length < 220 && looksHuman(args.lineage.how)) {
    bullets.push(args.lineage.how);
  }
  if (args.ruleTitle && looksHuman(args.ruleTitle)) {
    bullets.push(`Named check on file: ${args.ruleTitle}.`);
  }
  return bullets;
}

/** Problem, where, why — then a short fold for how the check was run. */
export function EvidenceStory({
  kind,
  fallbackTitle,
  lineage,
  evidence,
  lineIds,
  ruleTitle,
  policyRef,
  detector,
  approach,
  reviewReason,
  peer,
}: EvidenceStoryProps) {
  const copy = findingCopy(kind, fallbackTitle ?? "Pattern");
  const approachKey = approach ?? detector ?? "";
  const approachCopy = APPROACH_PLAIN[approachKey] ?? {
    label: "Paid-claim check",
    tech: "A check on paid claims",
  };
  const where = evidenceWhere(evidence, lineIds);
  const why = evidenceWhy(evidence);
  const how = howWeChecked({
    copySource: copy.source,
    approachLabel: approachCopy.tech,
    lineage,
    ruleTitle,
  });

  return (
    <div className="ev-story">
      <p className="ev-what">
        <strong>The problem.</strong> {copy.what}
      </p>
      {reviewReason ? <p>{reviewReason}</p> : null}
      {where.length > 0 ? (
        <>
          <p>
            <strong>Where it sits.</strong>
          </p>
          <dl className="facts dense">
            {where.map((row) => (
              <div key={row.label}>
                <dt>{row.label}</dt>
                <dd>{row.value}</dd>
              </div>
            ))}
          </dl>
        </>
      ) : null}
      {why.length > 0 ? (
        <>
          <p>
            <strong>Why it was flagged.</strong>
          </p>
          <dl className="facts dense">
            {why.map((row) => (
              <div key={row.label}>
                <dt>{row.label}</dt>
                <dd>{row.value}</dd>
              </div>
            ))}
          </dl>
        </>
      ) : null}
      <p>
        <strong>What to verify.</strong> {copy.check}
      </p>
      {peer}
      <div className="ev-tech is-open">
        <p>
          <strong>How we checked this.</strong>
        </p>
        <ul className="how-checked">
          {how.map((item) => (
            <li key={item}>{item}</li>
          ))}
        </ul>
        {lineage?.tables && lineage.tables.length > 0 ? (
          <details>
            <summary>Files used</summary>
            <SourceList tables={lineage.tables} compact />
          </details>
        ) : null}
        {policyRef ? <p className="muted">Policy on file: {policyRef}</p> : null}
      </div>
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
    ruleTitle: alert.rule_title,
    ruleVersion: alert.rule_version,
    policyRef: alert.policy_ref,
    detector: alert.detector,
    approach: alert.approach,
    score: alert.score,
    reviewReason: alert.review_reason,
  };
}
