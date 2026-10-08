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
  onRun: () => void;
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
}

function Slider({ id, label, value, display, min, max, step, hint, disabled, onChange }: SliderProps) {
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
      />
      <p id={`${id}-hint`} className="field-hint">
        {hint}
      </p>
    </div>
  );
}

/** Capacity, horizon, member weight and slot cap that drive the next queue recompute. */
export function DeskSettings({ draft, applied, deskHours, disabled, canRun, hasExtract, pending, onChange, onRun }: DeskSettingsProps) {
  const set = (patch: Partial<DeskDraft>) => onChange({ ...draft, ...patch });
  return (
    <Panel id="desk-settings" eyebrow="Settings" title="Desk capacity">
      <div className="desk-settings">
        <Slider
          id="capacity"
          label="Team investigation capacity"
          value={draft.capacity}
          display={`${draft.capacity.toFixed(0)} h`}
          min={8}
          max={80}
          step={1}
          hint={`Applied ${hours(applied.capacity)} · queued work ${hours(deskHours)}`}
          disabled={disabled}
          onChange={(capacity) => set({ capacity })}
        />
        <Slider
          id="member-weight"
          label="Member impact weight"
          value={draft.member}
          display={`${draft.member.toFixed(1)}×`}
          min={0.3}
          max={2.5}
          step={0.1}
          hint="Raises beneficiary harm relative to dollars."
          disabled={disabled}
          onChange={(member) => set({ member })}
        />
        <Slider
          id="max-slots"
          label="Today's recommended slots"
          value={draft.slots}
          display={String(draft.slots)}
          min={3}
          max={20}
          step={1}
          hint={`Applied cap ${applied.slots}. Extra cases stay on the tracked backlog.`}
          disabled={disabled}
          onChange={(slots) => set({ slots })}
        />
        <fieldset className="horizon">
          <legend className="slider-label">
            <span>Risk horizon</span>
            <span className="field-hint">Applied {applied.horizon} days</span>
          </legend>
          <div className="segmented">
            {[30, 60, 90].map((h) => (
              <button key={h} type="button" aria-pressed={draft.horizon === h} disabled={disabled} onClick={() => set({ horizon: h })}>
                {h} days
              </button>
            ))}
          </div>
        </fieldset>
        {canRun ? (
          <button type="button" className="btn solid" disabled={pending} onClick={onRun}>
            {pending ? (hasExtract ? "Re-laning…" : "Running detection…") : hasExtract ? "Recompute queue" : "Load tiny run"}
          </button>
        ) : null}
      </div>
    </Panel>
  );
}
