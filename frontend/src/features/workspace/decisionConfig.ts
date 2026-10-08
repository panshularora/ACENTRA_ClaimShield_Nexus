/**
 * Decision actions shown in the workspace DecisionBar.
 *
 * The backend is revising these (escalation to the state agency, suspension as a
 * manager-approved recommendation, follow-up decisions on needs_evidence cases). The bar
 * renders whatever this list holds, so the switch is a config change: add or rename an
 * action here and widen DecisionAction (api/types.ts) to match the API's accepted values.
 */
import type { DecisionAction } from "../../api/types";

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
}

export const DECISION_ACTIONS: readonly DecisionActionConfig[] = [
  {
    id: "needs_evidence",
    label: "Request more information",
    hint: "Hold the case until records, EVV, or interviews arrive.",
    ladder: ["medical_records_request", "prepayment_review"],
    defaultLadder: "medical_records_request",
    showsGaps: true,
  },
  {
    id: "escalate",
    label: "Refer for deeper review",
    hint: "Send to a fuller investigation or MFCU screening path.",
    ladder: ["mfcu_referral", "prepayment_review", "payment_suspension_recommend"],
    defaultLadder: "mfcu_referral",
  },
  {
    id: "monitor",
    label: "Keep under watch",
    hint: "Suspicion remains; do not close and do not treat as fraud.",
    ladder: ["education_letter", "prepayment_review"],
    defaultLadder: "education_letter",
  },
  {
    id: "dismiss",
    label: "Dismiss with reason",
    hint: "Evidence does not support concern. Document why.",
    ladder: [],
    defaultLadder: null,
  },
];

/** Pre-selected action; kept neutral so no outcome is suggested. */
export const DEFAULT_DECISION: DecisionAction = "monitor";

export const LADDER_LABELS: Record<string, string> = {
  education_letter: "Provider education letter",
  medical_records_request: "Medical records request",
  prepayment_review: "Prepayment review",
  mfcu_referral: "Referral to state MFCU",
  payment_suspension_recommend: "Recommend 42 CFR 455.23 payment suspension (state decides)",
};

export const REASON_MIN_LENGTH = 20;
