from __future__ import annotations

from datetime import UTC, datetime

from fastapi import APIRouter, Depends
from pydantic import BaseModel
from sqlalchemy.orm import Session

from claimshield.api.deps import check_csrf, get_db, require
from claimshield.core.errors import NotFound
from claimshield.db.models import User
from claimshield.wiki.service import (
    approve_proposal,
    proposal_for_decision,
    serialize_page,
    serialize_proposal,
)

router = APIRouter(prefix="/api/v1/decisions", tags=["decisions"])


class ApproveBody(BaseModel):
    note: str = ""


@router.post("/{decision_id}:approve", dependencies=[Depends(check_csrf)])
def post_approve_decision(
    decision_id: str,
    body: ApproveBody | None = None,
    session: Session = Depends(get_db),
    user: User = Depends(require("decision:approve")),
) -> dict:
    proposal = proposal_for_decision(session, decision_id)
    if proposal is None:
        raise NotFound("proposal not found for decision")
    page = approve_proposal(
        session,
        proposal=proposal,
        user=user,
        note=(body.note if body else "") or "",
        now=datetime.now(UTC),
    )
    return {
        "decision_id": decision_id,
        "proposal": serialize_proposal(proposal),
        "page": serialize_page(page),
    }
