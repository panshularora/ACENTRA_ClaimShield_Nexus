import { useState } from "react";
import type { CaseAlert, DecisionRecord, DecisionResult, WikiProposal } from "../../api/types";
import { alertLabel } from "../../lib/format";
import { ProposalCard } from "../wiki/ProposalCard";
import {
  DECISION_ACTIONS,
  DEFAULT_DECISION,
  LADDER_LABELS,
  REASON_MIN_LENGTH,
  type DecisionAction,
  type DecisionActionConfig,
} from "./decisionConfig";

function groupAlerts(alerts: CaseAlert[]): { key: string; rule: string; label: string; refs: string[] }[] {
  const map = new Map<string, { key: string; rule: string; label: string; refs: string[] }>();
  for (const alert of alerts) {
    const rule = alert.rule_id ?? alert.detector;
    const label = alertLabel(alert);
    const key = `${rule}|${label}`;
    const prev = map.get(key);
    const ref = `alert:${alert.alert_id}`;
    if (!prev) {
      map.set(key, { key, rule, label, refs: [ref] });
    } else if (!prev.refs.includes(ref)) {
      prev.refs.push(ref);
    }
  }
  return [...map.values()];
}

export function DecisionBar({
  actions = DECISION_ACTIONS,
  defaultAction = DEFAULT_DECISION,
  minReasonChars = REASON_MIN_LENGTH,
  disabled,
  blockedReason,
  gaps,
  pending,
  error,
  result,
  existingProposal,
  alerts,
  pendingDecision,
  canApprove,
  canReopen,
  reviewPending,
  onSubmit,
  onApprove,
  onReject,
  onReopen,
}: {
  actions?: readonly DecisionActionConfig[];
  defaultAction?: DecisionAction;
  minReasonChars?: number;
  disabled: boolean;
  blockedReason?: string | null;
  gaps: string[];
  pending: boolean;
  error: string | null;
  result: DecisionResult | null;
  existingProposal?: WikiProposal | null;
  alerts: CaseAlert[];
  pendingDecision?: DecisionRecord | null;
  canApprove?: boolean;
  canReopen?: boolean;
  reviewPending?: boolean;
  onSubmit: (
    action: DecisionAction,
    reason: string,
    evidenceRefs: string[],
    ladderStep: string | null,
  ) => void;
  onApprove?: (note: string) => void;
  onReject?: (note: string) => void;
  onReopen?: (reason: string) => void;
}) {
  const configFor = (id: DecisionAction) => actions.find((item) => item.id === id) ?? actions[0];
  const [action, setAction] = useState<DecisionAction>(configFor(defaultAction)?.id ?? DEFAULT_DECISION);
  const [ladder, setLadder] = useState<string | null>(configFor(defaultAction)?.defaultLadder ?? null);
  const [reason, setReason] = useState("");
  const [refs, setRefs] = useState<string[]>([]);
  const [reviewNote, setReviewNote] = useState("");
  const current = actions.find((item) => item.id === action) ?? actions.find((item) => item.id === defaultAction) ?? actions[0];
  const shownAction = current?.id ?? action;
  const ladderOptions = current?.ladder ?? [];
  const ladderMeta = current?.ladderMeta ?? [];
  const shownLadder = current && ladder && current.ladder.includes(ladder) ? ladder : (current?.defaultLadder ?? null);
  const ready = reason.trim().length >= minReasonChars && !disabled && !pending && Boolean(current);
  const proposal = result?.proposal ?? existingProposal ?? null;
  const busy = pending || Boolean(reviewPending);

  function chooseAction(next: DecisionAction) {
    setAction(next);
    setLadder(configFor(next).defaultLadder);
  }

  function toggleGroup(groupRefs: string[]) {
    setRefs((prev) => {
      const allOn = groupRefs.every((ref) => prev.includes(ref));
      if (allOn) return prev.filter((ref) => !groupRefs.includes(ref));
      return [...new Set([...prev, ...groupRefs])];
    });
  }

  function ladderLabel(step: string): string {
    return ladderMeta.find((item) => item.step === step)?.label ?? LADDER_LABELS[step] ?? step;
  }

  return (
    <div className="decision">
      {pendingDecision ? (
        <div className="banner warn" role="status">
          <p>
            <strong>Awaiting manager approval</strong>
          </p>
          <p>
            {pendingDecision.action}
            {pendingDecision.ladder_label ? ` · ${pendingDecision.ladder_label}` : ""} recorded by{" "}
            <span className="mono">{pendingDecision.actor_id}</span>. Escalation goes to the State Medicaid
            program integrity unit; payment suspension is the state&apos;s call.
          </p>
          {pendingDecision.reason ? <p>{pendingDecision.reason}</p> : null}
        </div>
      ) : null}

      {canApprove && pendingDecision && onApprove && onReject ? (
        <div className="decide-review">
          <label className="field">
            Approval or rejection note
            {pendingDecision.ladder_step === "payment_suspension_recommend"
              ? " (credible-allegation basis, at least 20 characters, for a payment-suspension recommendation)"
              : ""}
            <textarea
              rows={3}
              value={reviewNote}
              disabled={busy}
              onChange={(e) => setReviewNote(e.target.value)}
              placeholder="Why this escalation is approved or returned…"
            />
          </label>
          <div className="decide-review-actions">
            <button
              type="button"
              className="btn solid"
              disabled={busy}
              onClick={() => onApprove(reviewNote.trim())}
            >
              {reviewPending ? "Saving…" : "Approve escalation"}
            </button>
            <button
              type="button"
              className="btn"
              disabled={busy || reviewNote.trim().length < minReasonChars}
              onClick={() => onReject(reviewNote.trim())}
            >
              Return to investigator
            </button>
          </div>
        </div>
      ) : null}

      {canReopen && onReopen ? (
        <div className="decide-review">
          <p className="muted">This case is closed. A manager can reopen it for a follow-up decision.</p>
          {actions.length === 0 ? (
            <label className="field">
              Reopen reason (at least {minReasonChars} characters)
              <textarea
                rows={3}
                value={reason}
                disabled={busy}
                onChange={(e) => setReason(e.target.value)}
                placeholder="Why this case should be reopened…"
              />
            </label>
          ) : null}
          <button
            type="button"
            className="btn"
            disabled={busy || reason.trim().length < minReasonChars}
            onClick={() => onReopen(reason.trim())}
          >
            Reopen case
          </button>
        </div>
      ) : null}

      {actions.length > 0 ? (
        <div className="decide-grid">
          <fieldset className="decide-actions">
            <legend className="field">Action</legend>
            {actions.map((item) => (
              <label key={item.id} className={shownAction === item.id ? "on" : ""}>
                <input
                  type="radio"
                  name="decision-action"
                  value={item.id}
                  checked={shownAction === item.id}
                  disabled={disabled || busy}
                  onChange={() => chooseAction(item.id)}
                />
                <span className="decide-option">
                  <strong>
                    {item.label}
                    {item.requiresApproval ? " · manager approval" : ""}
                  </strong>
                  <span>{item.hint}</span>
                </span>
              </label>
            ))}
          </fieldset>
          <div className="decide-evidence">
            <p className="field">Supporting evidence reviewed</p>
            {alerts.length === 0 ? (
              <p className="muted">No findings to attach.</p>
            ) : (
              <ul className="ref-list">
                {groupAlerts(alerts).map((group) => {
                  const checked = group.refs.every((ref) => refs.includes(ref));
                  return (
                    <li key={group.key}>
                      <label>
                        <input
                          type="checkbox"
                          checked={checked}
                          disabled={disabled || busy}
                          onChange={() => toggleGroup(group.refs)}
                        />
                        <span className="mono">{group.rule}</span> {group.label}
                      </label>
                    </li>
                  );
                })}
              </ul>
            )}
            <label className="field decide-reason">
              Notes and rationale (at least {minReasonChars} characters)
              <textarea
                rows={3}
                value={reason}
                disabled={(disabled && !canReopen) || busy}
                onChange={(e) => setReason(e.target.value)}
                placeholder="What you verified, what remains uncertain, and why this next step…"
              />
              <span className="field-hint">
                {reason.trim().length}/{minReasonChars} characters
              </span>
            </label>
          </div>
          <div className="decide-side">
            {current?.showsGaps && gaps.length > 0 && (
              <div>
                <p className="field">Evidence still needed</p>
                <ul className="gap-list">
                  {gaps.map((g) => (
                    <li key={g}>{g}</li>
                  ))}
                </ul>
              </div>
            )}
            {ladderOptions.length > 0 && (
              <label className="field ladder-select">
                Program-integrity next step
                <select
                  value={shownLadder ?? ""}
                  disabled={disabled || busy}
                  onChange={(e) => setLadder(e.target.value || null)}
                >
                  {ladderOptions.map((step) => (
                    <option key={step} value={step}>
                      {ladderLabel(step)}
                    </option>
                  ))}
                </select>
                <span className="field-hint">
                  42 CFR 455.23 payment suspension is a recommendation. The state decides. Escalation is to the
                  State Medicaid program integrity unit, not the MFCU.
                </span>
              </label>
            )}
            <button
              type="button"
              className="btn solid"
              disabled={!ready}
              onClick={() => current && onSubmit(shownAction, reason.trim(), refs, shownLadder)}
            >
              {pending ? "Recording…" : current?.requiresApproval ? "Submit for manager approval" : "Record disposition"}
            </button>
          </div>
        </div>
      ) : blockedReason ? (
        <p className="muted">{blockedReason}</p>
      ) : null}

      {error && (
        <p className="error-text" role="alert">
          {error}
        </p>
      )}
      {result && (
        <div className="banner ok decide-receipt" role="status">
          <p>
            <strong>Audit confirmation</strong>
          </p>
          <p>
            {result.action} recorded
            {result.ladder_label ? ` · ${result.ladder_label}` : ""}
            {result.status ? ` · case ${result.status}` : ""}. {result.note}
          </p>
          <p className="mono muted">
            seq {result.audit.seq} · chain {result.audit.chain_intact ? "intact" : "broken"}
          </p>
        </div>
      )}
      {proposal && (
        <div className="proposal-embed">
          <ProposalCard proposal={proposal} compact={proposal.status !== "pending"} />
        </div>
      )}
    </div>
  );
}
