import { useState } from "react";
import type { CaseAlert, DecisionResult, WikiProposal } from "../../api/types";
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
    const label = alert.label ?? alert.rule_title ?? alert.detector;
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
  disabled,
  gaps,
  pending,
  error,
  result,
  existingProposal,
  alerts,
  onSubmit,
}: {
  /** Actions to offer; defaults to decisionConfig so the API's new set can be swapped in. */
  actions?: readonly DecisionActionConfig[];
  defaultAction?: DecisionAction;
  disabled: boolean;
  gaps: string[];
  pending: boolean;
  error: string | null;
  result: DecisionResult | null;
  existingProposal?: WikiProposal | null;
  alerts: CaseAlert[];
  onSubmit: (
    action: DecisionAction,
    reason: string,
    evidenceRefs: string[],
    ladderStep: string | null,
  ) => void;
}) {
  const configFor = (id: DecisionAction) => actions.find((item) => item.id === id) ?? actions[0];
  const [action, setAction] = useState<DecisionAction>(configFor(defaultAction).id);
  const [ladder, setLadder] = useState<string | null>(configFor(defaultAction).defaultLadder);
  const [reason, setReason] = useState("");
  const [refs, setRefs] = useState<string[]>([]);
  const ready = reason.trim().length >= REASON_MIN_LENGTH && !disabled && !pending;
  const proposal = result?.proposal ?? existingProposal ?? null;
  const current = configFor(action);
  const ladderOptions = current.ladder;

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

  return (
    <div className="decision">
      <div className="decide-grid">
        <fieldset className="decide-actions">
          <legend className="field">Action</legend>
          {actions.map((item) => (
            <label key={item.id} className={action === item.id ? "on" : ""}>
              <input
                type="radio"
                name="decision-action"
                value={item.id}
                checked={action === item.id}
                disabled={disabled || pending}
                onChange={() => chooseAction(item.id)}
              />
              <span className="decide-option">
                <strong>{item.label}</strong>
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
                        disabled={disabled || pending}
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
            Notes and rationale (at least {REASON_MIN_LENGTH} characters)
            <textarea
              rows={3}
              value={reason}
              disabled={disabled || pending}
              onChange={(e) => setReason(e.target.value)}
              placeholder="What you verified, what remains uncertain, and why this next step…"
            />
            <span className="field-hint">
              {reason.trim().length}/{REASON_MIN_LENGTH} characters
            </span>
          </label>
        </div>
        <div className="decide-side">
          {current.showsGaps && gaps.length > 0 && (
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
                value={ladder ?? ""}
                disabled={disabled || pending}
                onChange={(e) => setLadder(e.target.value || null)}
              >
                {ladderOptions.map((step) => (
                  <option key={step} value={step}>
                    {LADDER_LABELS[step] ?? step}
                  </option>
                ))}
              </select>
              <span className="field-hint">
                42 CFR 455.23 payment suspension is a recommendation. The state decides.
              </span>
            </label>
          )}
          <button
            type="button"
            className="btn solid"
            disabled={!ready}
            onClick={() => onSubmit(action, reason.trim(), refs, ladder)}
          >
            {pending ? "Recording…" : "Record disposition"}
          </button>
        </div>
      </div>
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
            {result.ladder_label ? ` · ${result.ladder_label}` : ""}. {result.note}
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
