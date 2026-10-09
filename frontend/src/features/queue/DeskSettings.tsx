import type { ReactNode } from "react";
import { Panel } from "../../components/ui/Panel";
import { hours } from "../../lib/format";

export interface DeskDraft {
  capacity: number;
  horizon: number;
  slots: number;
  member: number;
}

interface DeskSettingsProps {
  draft: DeskDraft;
  applied: DeskDraft;
  deskHours: number;
  disabled: boolean;
  canRun: boolean;
  hasExtract: boolean;
  pending: boolean;
  onChange: (draft: DeskDraft) => void;
  onRun: (draft: DeskDraft) => void;
  children?: ReactNode;
}

interface SliderProps {
  id: string;
  label: string;
  value: number;
  display: string;
  min: number;
  max: number;
  step: number;
  hint: string;
  disabled: boolean;
  onChange: (value: number) => void;
  onCommit: (value: number) => void;
}

function Slider({ id, label, value, display, min, max, step, hint, disabled, onChange, onCommit }: SliderProps) {
  const commit = (raw: string) => onCommit(Number(raw));
  return (
    <div className="slider">
      <label htmlFor={id} className="slider-label">
        <span>{label}</span>
        <strong className="num">{display}</strong>
      </label>
      <input
        id={id}
        type="range"
        min={min}
        max={max}
        step={step}
        value={value}
        disabled={disabled}
        aria-describedby={`${id}-hint`}
        onChange={(event) => onChange(Number(event.target.value))}
        onPointerUp={(event) => commit((event.target as HTMLInputElement).value)}
        onKeyUp={(event) => commit((event.target as HTMLInputElement).value)}
      />
      <p id={`${id}-hint`} className="field-hint">
        {hint}
      </p>
    </div>
  );
}

function sameDesk(a: DeskDraft, b: DeskDraft): boolean {
  return a.capacity === b.capacity && a.horizon === b.horizon && a.slots === b.slots && a.member === b.member;
}

/** Capacity, horizon, member weight and slot cap that drive the next queue recompute. */
export function DeskSettings({
  draft,
  applied,
  deskHours,
  disabled,
  canRun,
  hasExtract,
  pending,
  onChange,
  onRun,
  children,
}: DeskSettingsProps) {
  const set = (patch: Partial<DeskDraft>) => {
    const next = { ...draft, ...patch };
    onChange(next);
    return next;
  };
  const dirty = !sameDesk(draft, applied);
  return (
    <Panel id="desk-settings" eyebrow="Settings" title="Desk capacity">
      <div className="desk-settings">
        <Slider
          id="capacity"
          label="Hours"
          value={draft.capacity}
          display={`${draft.capacity.toFixed(0)} h`}
          min={8}
          max={80}
          step={1}
          hint={`Applied ${hours(applied.capacity)} · today's desk fills ${hours(deskHours)}`}
          disabled={disabled}
          onChange={(capacity) => set({ capacity })}
          onCommit={(capacity) => {
            const next = set({ capacity });
            if (!sameDesk(next, applied)) onRun(next);
          }}
        />
        <Slider
          id="member-weight"
          label="People weight"
          value={draft.member}
          display={`${draft.member.toFixed(1)}×`}
          min={0.3}
          max={2.5}
          step={0.1}
          hint="Raises beneficiary harm relative to dollars."
          disabled={disabled}
          onChange={(member) => set({ member })}
          onCommit={(member) => {
            const next = set({ member });
            if (!sameDesk(next, applied)) onRun(next);
          }}
        />
        <Slider
          id="max-slots"
          label="Slots"
          value={draft.slots}
          display={String(draft.slots)}
          min={3}
          max={20}
          step={1}
          hint={`Today's queue lists ${draft.slots} ranked cases. Extra stay on the tracked backlog.`}
          disabled={disabled}
          onChange={(slots) => set({ slots })}
          onCommit={(slots) => {
            const next = set({ slots });
            if (!sameDesk(next, applied)) onRun(next);
          }}
        />
        <fieldset className="horizon">
          <legend className="slider-label">
            <span>Window</span>
            <span className="field-hint">Applied {applied.horizon} days</span>
          </legend>
          <div className="segmented" role="group" aria-label="Look-ahead window">
            {[30, 60, 90].map((h) => (
              <button
                key={h}
                type="button"
                aria-pressed={draft.horizon === h}
                disabled={disabled}
                onClick={() => {
                  const next = set({ horizon: h });
                  if (!sameDesk(next, applied)) onRun(next);
                }}
              >
                {h} days
              </button>
            ))}
          </div>
        </fieldset>
        {canRun ? (
          <button type="button" className="btn solid" disabled={pending} onClick={() => onRun(draft)}>
            {pending
              ? hasExtract
                ? "Re-laning…"
                : "Running detection…"
              : hasExtract
                ? dirty
                  ? "Apply desk settings"
                  : "Recompute queue"
                : "Load tiny run"}
          </button>
        ) : null}
        {children}
      </div>
    </Panel>
  );
}
