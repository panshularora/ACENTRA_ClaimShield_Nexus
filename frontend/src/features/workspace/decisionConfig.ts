/**
 * Fallback decision actions if GET /cases/{id}/decision-options is unavailable.
 * The workspace prefers the API payload so ladders and approval flags stay in sync.
 */
import type { DecisionAction, DecisionOption, LadderStepOption } from "../../api/types";

export type { DecisionAction };

export interface DecisionActionConfig {
  id: DecisionAction;
  label: string;
  hint: string;
  /** Program-integrity next steps offered with this action (keys of LADDER_LABELS). */
  ladder: string[];
  defaultLadder: string | null;
  /** Show the case's open evidence gaps beside this action. */
  showsGaps?: boolean;
  requiresApproval?: boolean;
  ladderMeta?: LadderStepOption[];
}

export const DECISION_ACTIONS: readonly DecisionActionConfig[] = [
  {
    id: "needs_evidence",
    label: "Request more evidence",
    hint: "Keep the case open and request records; decide again when they arrive.",
    ladder: ["medical_records_request"],
    defaultLadder: "medical_records_request",
    showsGaps: true,
  },
  {
    id: "monitor",
    label: "Monitor",
    hint: "Keep the case open and watch for a recurrence; education letter by default.",
    ladder: ["education_letter"],
    defaultLadder: "education_letter",
  },
  {
    id: "escalate",
    label: "Escalate to the State Medicaid agency",
    hint: "Refer to the state program integrity unit. A manager must approve before the case closes.",
    ladder: ["state_pi_referral", "prepayment_review", "payment_suspension_recommend"],
    defaultLadder: "state_pi_referral",
    requiresApproval: true,
  },
  {
    id: "dismiss",
    label: "Dismiss with reason",
    hint: "Evidence does not support concern. Closes the case; a manager can reopen it.",
    ladder: [],
    defaultLadder: null,
  },
];

export function configsFromOptions(options: DecisionOption[]): DecisionActionConfig[] {
  return options
    .filter((option) => option.enabled)
    .map((option) => ({
      id: option.id,
      label: option.label,
      hint: option.hint,
      ladder: option.ladder.map((step) => step.step),
      defaultLadder: option.default_step,
      showsGaps: option.id === "needs_evidence",
      requiresApproval: option.requires_approval,
      ladderMeta: option.ladder,
    }));
}

/** Pre-selected action; kept neutral so no outcome is suggested. */
export const DEFAULT_DECISION: DecisionAction = "monitor";

export const LADDER_LABELS: Record<string, string> = {
  education_letter: "Provider education letter",
  medical_records_request: "Medical records request",
  prepayment_review: "Recommend prepayment review (state or plan policy)",
  state_pi_referral: "Refer to the State Medicaid agency program integrity unit (for MFCU consideration)",
  payment_suspension_recommend:
    "Recommend that the State Medicaid agency consider a 42 CFR 455.23 payment suspension (state agency decision; good-cause exceptions may apply)",
  mfcu_referral: "Referral to state MFCU (legacy step; referrals now go to the State Medicaid agency)",
};

export const REASON_MIN_LENGTH = 20;
