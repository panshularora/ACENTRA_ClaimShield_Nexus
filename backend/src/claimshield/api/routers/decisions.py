from __future__ import annotations

from datetime import UTC, datetime
from typing import Any

from fastapi import APIRouter, Depends
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from claimshield.api.deps import check_csrf, get_db, require
from claimshield.cases.decisions import MAX_REASON, approve_decision, get_decision_or_404, reject_decision
from claimshield.db.models import User

router = APIRouter(prefix="/api/v1/decisions", tags=["decisions"])


class ApproveBody(BaseModel):
    note: str = Field(
        default="",
        max_length=MAX_REASON,
        description="Required (20+ chars) for a payment-suspension recommendation: the credible-allegation basis.",
    )


class RejectBody(BaseModel):
    note: str = Field(min_length=1, max_length=MAX_REASON)


@router.post("/{decision_id}:approve", dependencies=[Depends(check_csrf)])
def post_approve_decision(
    decision_id: str,
    body: ApproveBody | None = None,
    session: Session = Depends(get_db),
    user: User = Depends(require("decision:approve")),
) -> dict[str, Any]:
    """Approve a pending escalation. The approver must not be the investigator who made it."""
    decision = get_decision_or_404(session, decision_id)
    return approve_decision(
        session, decision=decision, user=user, note=body.note if body else "", now=datetime.now(UTC)
    )


@router.post("/{decision_id}:reject", dependencies=[Depends(check_csrf)])
def post_reject_decision(
    decision_id: str,
    body: RejectBody,
    session: Session = Depends(get_db),
    user: User = Depends(require("decision:approve")),
) -> dict[str, Any]:
    """Send a pending escalation back; the case returns to the status it had before."""
    decision = get_decision_or_404(session, decision_id)
    return reject_decision(session, decision=decision, user=user, note=body.note, now=datetime.now(UTC))
