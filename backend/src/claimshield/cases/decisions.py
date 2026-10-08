"""Human decisions on cases: action ladder, approvals, reopen and the audit trail.

Workflow (every step writes a hash-chained audit event):

* Only the assigned investigator, or a user who can approve decisions (manager/admin), may
  decide a case. Unassigned cases must be taken first.
* ``monitor`` and ``needs_evidence`` keep the case open for a follow-up decision.
* ``escalate`` never closes a case directly. It records a pending decision; a different user
  with ``decision:approve`` approves (case becomes ``escalated``) or rejects it (case returns
  to its prior status). The default escalation is a referral to the State Medicaid agency's
  program integrity unit, which decides whether to refer to the MFCU.
* A payment-suspension step is only a recommendation to the State Medicaid agency, which
  makes the 42 CFR 455.23 determination; its approval must record the basis.
* ``escalated`` and ``dismissed`` are closed: a manager must reopen the case before anyone
  can decide it again.
"""

from __future__ import annotations

from datetime import datetime
from typing import Any

from sqlalchemy import select
from sqlalchemy.orm import Session

from claimshield.audit.service import append_event, chain_status
from claimshield.auth.rbac import has_permission
from claimshield.cases.common import iso
from claimshield.core.errors import Conflict, Forbidden, NotFound, ValidationFailed
from claimshield.core.ids import new_id
from claimshield.db.models import AuditEvent, Case, Decision, User
from claimshield.wiki.service import draft_precedent, serialize_label, serialize_proposal

MIN_REASON = 20
MAX_REASON = 4000
MAX_EVIDENCE_REFS = 50

ACTIONS = ("escalate", "monitor", "dismiss", "needs_evidence")
ACTION_STEPS: dict[str, tuple[str, ...]] = {
    "needs_evidence": ("medical_records_request",),
    "monitor": ("education_letter",),
    "escalate": ("state_pi_referral", "prepayment_review", "payment_suspension_recommend"),
    "dismiss": (),
}
DEFAULT_LADDER: dict[str, str | None] = {action: (steps[0] if steps else None) for action, steps in ACTION_STEPS.items()}
LADDER_LABELS = {
    "education_letter": "Provider education letter",
    "medical_records_request": "Medical records request",
    "state_pi_referral": "Refer to the State Medicaid agency program integrity unit (for MFCU consideration)",
    "prepayment_review": "Recommend prepayment review (state or plan policy)",
    "payment_suspension_recommend": (
        "Recommend that the State Medicaid agency consider a 42 CFR 455.23 payment suspension "
        "(state agency decision; good-cause exceptions may apply)"
    ),
    # Legacy step from earlier builds; kept so old decision rows still render.
    "mfcu_referral": "Referral to state MFCU (legacy step; referrals now go to the State Medicaid agency)",
}
ACTION_STATUS = {
    "escalate": "escalated",
    "monitor": "monitor",
    "dismiss": "dismissed",
    "needs_evidence": "needs_evidence",
}
PENDING_STATUS = "pending_approval"
CLOSED_STATUSES = frozenset({"escalated", "dismissed"})
APPROVAL_REQUIRED_ACTIONS = frozenset({"escalate"})
BASIS_REQUIRED_STEPS = frozenset({"payment_suspension_recommend"})
NOTE = "Potential FWA pattern requiring investigation. This is not an automatic fraud label."


def is_approver(user: User) -> bool:
    return has_permission(user.role, "decision:approve")


def decision_block_reason(case: Case, user: User) -> str | None:
    """Why ``user`` cannot decide ``case`` right now, or None when they can."""
    if not has_permission(user.role, "case:decide"):
        return "role lacks case:decide"
    if case.status in CLOSED_STATUSES:
        return "case is closed; a manager must reopen it before a new decision"
    if case.status == PENDING_STATUS:
        return "an escalation on this case is awaiting manager approval"
    if is_approver(user):
        return None
    if case.assignee_id is None:
        return "take ownership of the case before deciding it"
    if case.assignee_id != user.id:
        return "only the assigned investigator or a manager can decide this case"
    return None


def pending_decision(session: Session, case_id: str) -> Decision | None:
    stmt = (
        select(Decision)
        .where(Decision.case_id == case_id, Decision.status == PENDING_STATUS)
        .order_by(Decision.created_at.desc())
    )
    return session.execute(stmt).scalars().first()


def allowed_actions(session: Session, case: Case, user: User) -> list[str]:
    """Workflow verbs this user may use on the case now (drives the decision bar)."""
    verbs: list[str] = []
    if decision_block_reason(case, user) is None:
        verbs.extend(ACTIONS)
    pending = pending_decision(session, case.case_id) if case.status == PENDING_STATUS else None
    if pending is not None and is_approver(user) and pending.actor_id != user.id:
        verbs.extend(["approve", "reject"])
    if case.status in CLOSED_STATUSES and is_approver(user):
        verbs.append("reopen")
    return verbs


def decision_options() -> dict[str, list[dict[str, Any]]]:
    """Ladder steps per action, with defaults and whether a manager must approve."""
    return {
        action: [
            {
                "step": step,
                "label": LADDER_LABELS[step],
                "default": step == DEFAULT_LADDER[action],
                "requires_approval": action in APPROVAL_REQUIRED_ACTIONS,
                "requires_basis_on_approval": step in BASIS_REQUIRED_STEPS,
            }
            for step in steps
        ]
        for action, steps in ACTION_STEPS.items()
    }


def serialize_decision(row: Decision) -> dict[str, Any]:
    return {
        "decision_id": row.decision_id,
        "case_id": row.case_id,
        "actor_id": row.actor_id,
        "action": row.action,
        "status": row.status,
        "ladder_step": row.ladder_step,
        "ladder_label": LADDER_LABELS.get(row.ladder_step) if row.ladder_step else None,
        "reason": row.reason,
        "evidence_refs": row.evidence_refs or [],
        "requires_approval": row.action in APPROVAL_REQUIRED_ACTIONS,
        "approved_by": row.approved_by,
        "approved_at": iso(row.approved_at),
        "review_note": row.review_note,
        "created_at": iso(row.created_at),
    }


def _clean_text(value: str | None, *, field: str, minimum: int) -> str:
    text = (value or "").strip()
    if len(text) < minimum:
        raise ValidationFailed(f"{field} must be at least {minimum} characters")
    if len(text) > MAX_REASON:
        raise ValidationFailed(f"{field} must be at most {MAX_REASON} characters")
    return text


def _audit_payload(event: AuditEvent, session: Session, user: User, case: Case, reason: str) -> dict[str, Any]:
    verification = chain_status(session)
    return {
        "seq": event.seq,
        "hash": event.hash,
        "prev_hash": event.prev_hash,
        "ts": iso(event.ts),
        "action": event.action,
        "actor": user.display_name,
        "actor_id": user.id,
        "case_id": case.case_id,
        "reason": reason,
        "chain_intact": verification["intact"],
        "last_seq": verification["last_seq"],
    }


def record_decision(
    session: Session,
    *,
    case: Case,
    user: User,
    action: str,
    reason: str,
    ladder_step: str | None,
    evidence_refs: list[str],
    now: datetime,
) -> dict[str, Any]:
    if action not in ACTIONS:
        raise ValidationFailed("action must be escalate, monitor, dismiss, or needs_evidence")
    text = _clean_text(reason, field="reason", minimum=MIN_REASON)
    if len(evidence_refs) > MAX_EVIDENCE_REFS:
        raise ValidationFailed(f"at most {MAX_EVIDENCE_REFS} evidence references")
    step = ladder_step or DEFAULT_LADDER[action]
    if step is not None and step not in ACTION_STEPS[action]:
        raise ValidationFailed(f"ladder_step {step!r} is not a {action} step")
    blocked = decision_block_reason(case, user)
    if blocked:
        if case.status in CLOSED_STATUSES or case.status == PENDING_STATUS:
            raise Conflict(blocked, case_id=case.case_id)
        raise Forbidden(blocked, case_id=case.case_id)
    needs_approval = action in APPROVAL_REQUIRED_ACTIONS
    prior = case.status
    case.status = PENDING_STATUS if needs_approval else ACTION_STATUS[action]
    row = Decision(
        decision_id=new_id("DEC"),
        case_id=case.case_id,
        actor_id=user.id,
        action=action,
        status=PENDING_STATUS if needs_approval else "recorded",
        prior_status=prior,
        ladder_step=step,
        reason=text,
        evidence_refs=evidence_refs,
        approved_by=None,
        created_at=now,
    )
    session.add(row)
    event = append_event(
        session,
        actor_id=user.id,
        role=user.role,
        action="case.decide",
        object_type="case",
        object_id=case.case_id,
        payload={
            "decision_id": row.decision_id,
            "action": action,
            "status": case.status,
            "prior_status": prior,
            "ladder_step": step,
            "ladder_label": LADDER_LABELS.get(step) if step else None,
            "requires_approval": needs_approval,
        },
        ts=now,
    )
    session.flush()
    proposal = label = None
    if not needs_approval:
        proposal, label = draft_precedent(session, case=case, decision=row, user=user, now=now)
    return {
        **serialize_decision(row),
        "status": case.status,
        "decision_status": row.status,
        "audit": _audit_payload(event, session, user, case, text),
        "proposal": serialize_proposal(proposal) if proposal else None,
        "label": serialize_label(label) if label else None,
        "note": NOTE,
    }


def get_decision_or_404(session: Session, decision_id: str) -> Decision:
    row = session.get(Decision, decision_id)
    if row is None:
        raise NotFound("decision not found")
    return row


def _review_guard(session: Session, decision: Decision, user: User) -> Case:
    if not is_approver(user):
        raise Forbidden("role lacks decision:approve")
    if decision.status != PENDING_STATUS:
        raise Conflict("decision is not awaiting approval")
    if decision.actor_id == user.id:
        raise Forbidden("a decision cannot be approved or rejected by the person who made it")
    case = session.get(Case, decision.case_id)
    if case is None:
        raise NotFound("case not found")
    return case


def approve_decision(
    session: Session, *, decision: Decision, user: User, note: str | None, now: datetime
) -> dict[str, Any]:
    case = _review_guard(session, decision, user)
    minimum = MIN_REASON if decision.ladder_step in BASIS_REQUIRED_STEPS else 0
    text = _clean_text(note, field="approval note (credible-allegation basis)" if minimum else "note", minimum=minimum)
    decision.status = "approved"
    decision.approved_by = user.id
    decision.approved_at = now
    decision.review_note = text or None
    case.status = ACTION_STATUS[decision.action]
    event = append_event(
        session,
        actor_id=user.id,
        role=user.role,
        action="case.decision.approve",
        object_type="case",
        object_id=case.case_id,
        payload={
            "decision_id": decision.decision_id,
            "decided_by": decision.actor_id,
            "ladder_step": decision.ladder_step,
            "status": case.status,
        },
        ts=now,
    )
    session.flush()
    proposal, label = draft_precedent(session, case=case, decision=decision, user=user, now=now)
    return {
        "decision": serialize_decision(decision),
        "case_id": case.case_id,
        "status": case.status,
        "audit": _audit_payload(event, session, user, case, text),
        "proposal": serialize_proposal(proposal),
        "label": serialize_label(label),
        "note": NOTE,
    }


def reject_decision(
    session: Session, *, decision: Decision, user: User, note: str | None, now: datetime
) -> dict[str, Any]:
    case = _review_guard(session, decision, user)
    text = _clean_text(note, field="reject note", minimum=MIN_REASON)
    decision.status = "rejected"
    decision.review_note = text
    case.status = decision.prior_status or "open"
    event = append_event(
        session,
        actor_id=user.id,
        role=user.role,
        action="case.decision.reject",
        object_type="case",
        object_id=case.case_id,
        payload={"decision_id": decision.decision_id, "decided_by": decision.actor_id, "status": case.status},
        ts=now,
    )
    session.flush()
    return {
        "decision": serialize_decision(decision),
        "case_id": case.case_id,
        "status": case.status,
        "audit": _audit_payload(event, session, user, case, text),
    }


def reopen_case(session: Session, *, case: Case, user: User, reason: str, now: datetime) -> dict[str, Any]:
    if not is_approver(user):
        raise Forbidden("only a manager can reopen a closed case")
    if case.status not in CLOSED_STATUSES:
        raise Conflict("only escalated or dismissed cases can be reopened", case_id=case.case_id)
    text = _clean_text(reason, field="reason", minimum=MIN_REASON)
    prior = case.status
    case.status = "open"
    event = append_event(
        session,
        actor_id=user.id,
        role=user.role,
        action="case.reopen",
        object_type="case",
        object_id=case.case_id,
        payload={"prior_status": prior, "status": case.status, "reason": text},
        ts=now,
    )
    session.flush()
    return {
        "case_id": case.case_id,
        "status": case.status,
        "prior_status": prior,
        "audit": _audit_payload(event, session, user, case, text),
    }
