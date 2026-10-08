import { useState } from "react";

export interface OverrideTarget {
  caseId: string;
  action: "promote" | "defer";
}

interface OverrideFormProps {
  target: OverrideTarget;
  pending: boolean;
  onCancel: () => void;
  onSubmit: (reason: string) => void;
}

const MIN_REASON = 20;

/** Human-in-the-loop promote/defer with a mandatory written reason. */
export function OverrideForm({ target, pending, onCancel, onSubmit }: OverrideFormProps) {
  const [reason, setReason] = useState("");
  const trimmed = reason.trim();
  return (
    <section className="panel override-form" aria-labelledby="override-title">
      <div className="panel-body">
        <div className="panel-head-text">
          <p className="kicker">Human override · {target.caseId}</p>
          <h2 id="override-title">
            {target.action === "promote" ? "Promote onto today's desk" : "Defer to the tracked backlog"}
          </h2>
          <p className="muted">
            {target.action === "promote"
              ? "This does not label fraud. It only asks SIU to work the case now."
              : "Defer keeps the case open. It is not a dismissal."}
          </p>
        </div>
        <label className="field">
          Reason (required, at least {MIN_REASON} characters)
          <textarea
            rows={3}
            value={reason}
            onChange={(event) => setReason(event.target.value)}
            placeholder="Why this override, in language another reviewer can follow…"
          />
          <span className="field-hint">
            {trimmed.length}/{MIN_REASON} characters
          </span>
        </label>
        <div className="chip-row">
          <button
            type="button"
            className="btn solid"
            disabled={trimmed.length < MIN_REASON || pending}
            onClick={() => onSubmit(trimmed)}
          >
            {pending ? "Recording…" : "Record override"}
          </button>
          <button type="button" className="btn ghost" onClick={onCancel}>
            Cancel
          </button>
        </div>
      </div>
    </section>
  );
}
