import { useQuery } from "@tanstack/react-query";
import type { AlertLineage, CaseAlert } from "../../api/types";
import { api } from "../../api/client";
import { Drawer } from "../../components/ui/Drawer";
import { ErrorState, LoadingState } from "../../components/ui/States";
import { money, pct } from "../../lib/format";
import { findingCopy, kindTitle } from "../../lib/plainLanguage";
import { EvidenceStory } from "./EvidenceStory";
import { PeerCompare } from "./PeerCompare";

function isRecord(value: unknown): value is Record<string, unknown> {
  return typeof value === "object" && value !== null;
}

function str(value: unknown): string | null {
  return typeof value === "string" && value ? value : null;
}

function num(value: unknown): number | null {
  return typeof value === "number" && Number.isFinite(value) ? value : null;
}

function AlertBody({ payload }: { payload: Record<string, unknown> }) {
  const alert = payload as unknown as CaseAlert;
  const kind = str(payload.kind) ?? (typeof alert.evidence?.kind === "string" ? alert.evidence.kind : undefined);
  const lineage = isRecord(payload.lineage) ? (payload.lineage as unknown as AlertLineage) : alert.lineage;
  const lineIds = Array.isArray(payload.line_ids)
    ? payload.line_ids.filter((id): id is string => typeof id === "string")
    : alert.line_ids;
  return (
    <EvidenceStory
      kind={kind}
      fallbackTitle={str(payload.label) ?? undefined}
      lineage={lineage}
      evidence={alert.evidence}
      lineIds={lineIds}
      ruleId={str(payload.rule_id) ?? alert.rule_id}
      ruleVersion={num(payload.rule_version) ?? alert.rule_version}
      policyRef={str(payload.policy_ref) ?? alert.policy_ref}
      detector={str(payload.detector) ?? alert.detector}
      approach={str(payload.approach) ?? alert.approach}
      score={num(payload.score) ?? alert.score}
      peer={alert.evidence?.peer_group ? <PeerCompare evidence={alert.evidence} /> : null}
    />
  );
}

function LineBody({ payload }: { payload: Record<string, unknown> }) {
  const paid = num(payload.paid);
  const units = num(payload.units);
  return (
    <div className="ev-story">
      <p className="ev-what">This is one service on a paid claim that a pattern pointed at.</p>
      <p>
        <strong>What to check.</strong> Confirm the code, date, units and paid amount against the claim image.
      </p>
      <dl className="facts dense">
        {str(payload.code) ? (
          <div>
            <dt>Service code</dt>
            <dd className="mono">{str(payload.code)}</dd>
          </div>
        ) : null}
        {str(payload.dos_from) ? (
          <div>
            <dt>Date of service</dt>
            <dd>{str(payload.dos_from)}</dd>
          </div>
        ) : null}
        {paid != null ? (
          <div>
            <dt>Paid</dt>
            <dd>{money(paid)}</dd>
          </div>
        ) : null}
        {units != null ? (
          <div>
            <dt>Units</dt>
            <dd>{units}</dd>
          </div>
        ) : null}
        {str(payload.billing_provider_id) ? (
          <div>
            <dt>Billing provider</dt>
            <dd className="mono">{str(payload.billing_provider_id)}</dd>
          </div>
        ) : null}
      </dl>
      <details className="ev-tech">
        <summary>Technical — claim-line fields</summary>
        <p>Table <span className="mono">claim_line</span> joined to the paid claim header.</p>
        {str(payload.line_id) ? (
          <p className="mono muted">{str(payload.line_id)}</p>
        ) : null}
        {str(payload.claim_id) ? (
          <p className="mono muted">{str(payload.claim_id)}</p>
        ) : null}
      </details>
    </div>
  );
}

function MetricBody({ payload }: { payload: Record<string, unknown> }) {
  return (
    <div className="ev-story">
      <p className="ev-what">These are the case scores. They rank work for a person. They do not close the case.</p>
      <dl className="facts dense">
        <div>
          <dt>Suspicion</dt>
          <dd>{pct(num(payload.p_confirm))}</dd>
        </div>
        <div>
          <dt>Scheme severity</dt>
          <dd>{num(payload.severity) ?? "—"} of 4</dd>
        </div>
        <div>
          <dt>Financial exposure</dt>
          <dd>{num(payload.flagged_dollars) != null ? money(payload.flagged_dollars as number) : "—"}</dd>
        </div>
        <div>
          <dt>Member impact</dt>
          <dd>
            Harm {num(payload.harm) ?? "—"} · {num(payload.members_affected) ?? "—"} people
          </dd>
        </div>
        <div>
          <dt>Evidence strength</dt>
          <dd>{pct(num(payload.evidence_strength))}</dd>
        </div>
      </dl>
      <details className="ev-tech">
        <summary>Technical — score field</summary>
        <p>
          Cited field <span className="mono">{str(payload.field) ?? "metric"}</span>. Suspicion is a model score.
          Desk rank is a separate five-factor mix.
        </p>
      </details>
    </div>
  );
}

function ProviderBody({ payload }: { payload: Record<string, unknown> }) {
  return (
    <div className="ev-story">
      <p className="ev-what">The provider this case is about, from the enrollment file.</p>
      <dl className="facts dense">
        {str(payload.name) ? (
          <div>
            <dt>Name</dt>
            <dd>{str(payload.name)}</dd>
          </div>
        ) : null}
        {str(payload.npi_syn) || str(payload.npi) ? (
          <div>
            <dt>NPI</dt>
            <dd className="mono">{str(payload.npi_syn) ?? str(payload.npi)}</dd>
          </div>
        ) : null}
        {str(payload.specialty) ? (
          <div>
            <dt>Specialty</dt>
            <dd>{str(payload.specialty)?.replaceAll("_", " ")}</dd>
          </div>
        ) : null}
      </dl>
      <details className="ev-tech">
        <summary>Technical — enrollment row</summary>
        <p>
          Table <span className="mono">provider</span>
          {str(payload.provider_id) ? (
            <>
              {" "}
              · id <span className="mono">{str(payload.provider_id)}</span>
            </>
          ) : null}
          .
        </p>
      </details>
    </div>
  );
}

/** Side drawer that explains one cited item in plain words, then the technical method. */
export function EvidenceDrawer({ caseId, itemId, onClose }: { caseId: string; itemId: string; onClose: () => void }) {
  const query = useQuery({
    queryKey: ["evidence", caseId, itemId],
    queryFn: () => api.getEvidence(caseId, itemId),
  });
  const payload = query.data?.payload;
  const kind = query.data?.kind ?? itemId.split(":")[0];
  const title =
    payload && isRecord(payload)
      ? findingCopy(str(payload.kind) ?? undefined, str(payload.label) ?? kindTitle(kind)).title
      : kindTitle(kind);

  return (
    <Drawer titleId="ev-title" eyebrow="Evidence item" title={title} subtitle={itemId} onClose={onClose}>
      {query.isLoading ? <LoadingState label="Loading…" /> : null}
      {query.error ? <ErrorState title="Could not load this item" error={query.error} /> : null}
      {query.data && payload && isRecord(payload) ? (
        <>
          {kind === "alert" ? <AlertBody payload={payload} /> : null}
          {kind === "line" ? <LineBody payload={payload} /> : null}
          {kind === "claim" ? (
            <div className="ev-story">
              <p className="ev-what">A paid claim with one or more lines that a pattern pointed at.</p>
              {Array.isArray(payload.lines) ? (
                <p>{payload.lines.length} line{payload.lines.length === 1 ? "" : "s"} on this claim in the case extract.</p>
              ) : null}
              <details className="ev-tech">
                <summary>Technical — claim header</summary>
                <p>
                  Table <span className="mono">claim</span>
                  {str(payload.claim_id) ? (
                    <>
                      {" "}
                      · <span className="mono">{str(payload.claim_id)}</span>
                    </>
                  ) : null}
                  .
                </p>
              </details>
            </div>
          ) : null}
          {kind === "metric" ? <MetricBody payload={payload} /> : null}
          {kind === "provider" || kind === "node" ? <ProviderBody payload={payload} /> : null}
          {kind === "edge" ? (
            <div className="ev-story">
              <p className="ev-what">A recorded link between two parties on this case (ownership, referral, or shared contact).</p>
              <p>
                <strong>What to check.</strong> Confirm the shared identifier and which NPI billed the flagged lines.
              </p>
              <details className="ev-tech" open>
                <summary>Technical — graph edge</summary>
                {str(payload.kind) ? (
                  <p>
                    Edge kind <span className="mono">{str(payload.kind)}</span>
                  </p>
                ) : null}
                {str(payload.source) && str(payload.target) ? (
                  <p className="mono">
                    {str(payload.source)} → {str(payload.target)}
                  </p>
                ) : null}
              </details>
            </div>
          ) : null}
          {kind === "precedent" ? (
            <div className="ev-story">
              <p className="ev-what">An earlier reviewed case used as a comparison, not as proof of this one.</p>
              {str(payload.title) ? <p>{str(payload.title)}</p> : null}
            </div>
          ) : null}
        </>
      ) : null}
    </Drawer>
  );
}
