"""Human decisions on cases: action ladder, decision records and the audit trail."""

from __future__ import annotations

from datetime import datetime
from typing import Any

from sqlalchemy.orm import Session

from claimshield.audit.service import append_event, chain_status
from claimshield.cases.common import iso
from claimshield.core.errors import ValidationFailed
from claimshield.core.ids import new_id
from claimshield.db.models import Case, Decision, User
from claimshield.wiki.service import draft_precedent, serialize_label, serialize_proposal

ACTIONS = ("escalate", "monitor", "dismiss", "needs_evidence")
LADDER_STEPS = (
    "education_letter",
    "medical_records_request",
    "prepayment_review",
    "mfcu_referral",
    "payment_suspension_recommend",
)
DEFAULT_LADDER = {
    "needs_evidence": "medical_records_request",
    "escalate": "mfcu_referral",
    "monitor": "education_letter",
    "dismiss": None,
}
LADDER_LABELS = {
    "education_letter": "Provider education letter",
    "medical_records_request": "Medical records request",
    "prepayment_review": "Prepayment review",
    "mfcu_referral": "Referral to state MFCU",
    "payment_suspension_recommend": "Recommend 42 CFR 455.23 payment suspension (state decides)",
}
ACTION_STATUS = {
    "escalate": "escalated",
    "monitor": "monitor",
    "dismiss": "dismissed",
    "needs_evidence": "needs_evidence",
}


def serialize_decision(row: Decision) -> dict[str, Any]:
    return {
        "decision_id": row.decision_id,
        "case_id": row.case_id,
        "actor_id": row.actor_id,
        "action": row.action,
        "ladder_step": row.ladder_step,
        "ladder_label": LADDER_LABELS.get(row.ladder_step) if row.ladder_step else None,
        "reason": row.reason,
        "evidence_refs": row.evidence_refs or [],
        "approved_by": row.approved_by,
        "created_at": iso(row.created_at),
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
    text = (reason or "").strip()
    if len(text) < 20:
        raise ValidationFailed("reason must be at least 20 characters")
    step = ladder_step or DEFAULT_LADDER.get(action)
    if step and step not in LADDER_STEPS:
        raise ValidationFailed("ladder_step is not a program-integrity action")
    case.status = ACTION_STATUS[action]
    row = Decision(
        decision_id=new_id("DEC"),
        case_id=case.case_id,
        actor_id=user.id,
        action=action,
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
            "ladder_step": step,
            "ladder_label": LADDER_LABELS.get(step) if step else None,
        },
        ts=now,
    )
    session.flush()
    proposal, label = draft_precedent(session, case=case, decision=row, user=user, now=now)
    verification = chain_status(session)
    return {
        "decision_id": row.decision_id,
        "case_id": case.case_id,
        "action": action,
        "status": case.status,
        "reason": text,
        "ladder_step": step,
        "ladder_label": LADDER_LABELS.get(step) if step else None,
        "evidence_refs": evidence_refs,
        "created_at": iso(row.created_at),
        "audit": {
            "seq": event.seq,
            "hash": event.hash,
            "prev_hash": event.prev_hash,
            "ts": iso(event.ts),
            "action": event.action,
            "actor": user.display_name,
            "actor_id": user.id,
            "case_id": case.case_id,
            "reason": text,
            "chain_intact": verification["intact"],
            "last_seq": verification["last_seq"],
        },
        "proposal": serialize_proposal(proposal),
        "label": serialize_label(label),
        "note": "Potential FWA pattern requiring investigation. This is not an automatic fraud label.",
    }

