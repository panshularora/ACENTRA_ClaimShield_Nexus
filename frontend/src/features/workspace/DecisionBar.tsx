import { useState } from "react";
import type { DecisionResult } from "../../api/types";

const ACTIONS = [
  { id: "escalate" as const, label: "Escalate", hint: "Refer for further SIU / MFCU consideration." },
  { id: "monitor" as const, label: "Monitor", hint: "Watch for displacement; do not close." },
  { id: "dismiss" as const, label: "Dismiss", hint: "Close as not a screening lead." },
  { id: "needs_evidence" as const, label: "Needs more evidence", hint: "Hold until records arrive." },
];

export function DecisionBar({
  disabled,
  gaps,
  pending,
  error,
  result,
  onSubmit,
}: {
  disabled: boolean;
  gaps: string[];
  pending: boolean;
  error: string | null;
  result: DecisionResult | null;
  onSubmit: (action: (typeof ACTIONS)[number]["id"], reason: string) => void;
}) {
  const [action, setAction] = useState<(typeof ACTIONS)[number]["id"]>("monitor");
  const [reason, setReason] = useState("");
  const ready = reason.trim().length >= 20 && !disabled && !pending;

  return (
    <section className="ws-panel ws-decide" aria-labelledby="decide-title">
      <header className="ws-panel-head">
        <div>
          <p className="kicker">Decision bar</p>
          <h2 id="decide-title">Human decision</h2>
        </div>
        <p className="muted">A reason of at least 20 characters is required. This never auto-labels fraud.</p>
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
        <label className="decide-reason">
          Reason
          <textarea
            rows={3}
            value={reason}
            disabled={disabled || pending}
            onChange={(e) => setReason(e.target.value)}
            placeholder="Cite the evidence you reviewed and the screening recommendation…"
          />
          <span className="muted mono">{reason.trim().length}/20</span>
        </label>
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
            onClick={() => onSubmit(action, reason.trim())}
          >
            {pending ? "Recording…" : "Record decision"}
          </button>
        </div>
      </div>
      {error && <p className="error-text">{error}</p>}
      {result && (
        <div className="banner ok decide-receipt" role="status">
          <p>
            Recorded <strong>{result.action}</strong>. Case status is now{" "}
            <span className="mono">{result.status}</span>. {result.note}
          </p>
          <p className="mono">
            {result.decision_id} · audit seq {result.audit.seq} · {result.audit.hash}
          </p>
        </div>
      )}
    </section>
  );
}
