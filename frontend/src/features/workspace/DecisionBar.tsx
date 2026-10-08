import { useState } from "react";
import type { CaseAlert, DecisionResult, WikiProposal } from "../../api/types";
import { ProposalCard } from "../wiki/ProposalCard";

const ACTIONS = [
  {
    id: "needs_evidence" as const,
    label: "Request more information",
    hint: "Hold the case until records, EVV, or interviews arrive.",
  },
  {
    id: "escalate" as const,
    label: "Refer for deeper review",
    hint: "Send to a fuller investigation or MFCU screening path.",
  },
  {
    id: "monitor" as const,
    label: "Keep under watch",
    hint: "Suspicion remains; do not close and do not treat as fraud.",
  },
  {
    id: "dismiss" as const,
    label: "Dismiss with reason",
    hint: "Evidence does not support concern. Document why.",
  },
];

export function DecisionBar({
  disabled,
  gaps,
  pending,
  error,
  result,
  existingProposal,
  alerts,
  onSubmit,
}: {
  disabled: boolean;
  gaps: string[];
  pending: boolean;
  error: string | null;
  result: DecisionResult | null;
  existingProposal?: WikiProposal | null;
  alerts: CaseAlert[];
  onSubmit: (
    action: (typeof ACTIONS)[number]["id"],
    reason: string,
    evidenceRefs: string[],
  ) => void;
}) {
  const [action, setAction] = useState<(typeof ACTIONS)[number]["id"]>("monitor");
  const [reason, setReason] = useState("");
  const [refs, setRefs] = useState<string[]>([]);
  const ready = reason.trim().length >= 20 && !disabled && !pending;
  const proposal = result?.proposal ?? existingProposal ?? null;

  function toggle(ref: string) {
    setRefs((prev) => (prev.includes(ref) ? prev.filter((x) => x !== ref) : [...prev, ref]));
  }

  return (
    <section className="ws-panel ws-decide" aria-labelledby="decide-title">
      <header className="ws-panel-head">
        <div>
          <p className="kicker">Disposition · human only</p>
          <h2 id="decide-title">Record the next step</h2>
        </div>
        <p className="muted">
          An alert is suspicion, not a confirmed finding of fraud. Cite the evidence you inspected
          and write a reason another reviewer can follow.
        </p>
      </header>
      <div className="decide-grid">
        <fieldset className="decide-actions">
          <legend className="sr">Action</legend>
          {ACTIONS.map((item) => (
            <label key={item.id} className={action === item.id ? "on" : ""}>
              <input
                type="radio"
                name="decision-action"
                value={item.id}
                checked={action === item.id}
                disabled={disabled || pending}
                onChange={() => setAction(item.id)}
              />
              <strong>{item.label}</strong>
              <span>{item.hint}</span>
            </label>
          ))}
        </fieldset>
        <div>
          <p className="kicker">Supporting evidence reviewed</p>
          {alerts.length === 0 ? (
            <p className="muted">No findings to attach.</p>
          ) : (
            <ul className="ref-list">
              {alerts.map((alert) => {
                const ref = `alert:${alert.alert_id}`;
                return (
                  <li key={alert.alert_id}>
                    <label>
                      <input
                        type="checkbox"
                        checked={refs.includes(ref)}
                        disabled={disabled || pending}
                        onChange={() => toggle(ref)}
                      />
                      <span className="mono">{alert.rule_id ?? alert.detector}</span> {alert.label}
                    </label>
                  </li>
                );
              })}
            </ul>
          )}
          <label className="decide-reason">
            Notes and override rationale
            <textarea
              rows={3}
              value={reason}
              disabled={disabled || pending}
              onChange={(e) => setReason(e.target.value)}
              placeholder="What you verified, what remains uncertain, and why this next step…"
            />
            <span className="muted mono">{reason.trim().length}/20</span>
          </label>
        </div>
        <div className="decide-side">
          {action === "needs_evidence" && gaps.length > 0 && (
            <div>
              <p className="kicker">Evidence still needed</p>
              <ul className="gap-list">
                {gaps.map((g) => (
                  <li key={g}>{g}</li>
                ))}
              </ul>
            </div>
          )}
          <button
            type="button"
            className="btn solid"
            disabled={!ready}
            onClick={() => onSubmit(action, reason.trim(), refs)}
          >
            {pending ? "Recording…" : "Record disposition"}
          </button>
        </div>
      </div>
      {error && <p className="error-text">{error}</p>}
      {result && (
        <div className="banner ok decide-receipt" role="status">
          <p className="kicker">Audit confirmation</p>
          <p>
            {result.action} recorded. {result.note}
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
    </section>
  );
}
