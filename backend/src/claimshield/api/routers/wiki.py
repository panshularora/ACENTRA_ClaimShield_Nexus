from __future__ import annotations

from datetime import UTC, datetime

from fastapi import APIRouter, Depends, Query
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from claimshield.api.deps import check_csrf, get_db, require
from claimshield.cases.decisions import MAX_REASON
from claimshield.db.models import User
from claimshield.wiki.service import (
    approve_proposal,
    get_page,
    get_proposal,
    list_pages,
    list_proposals,
    reject_proposal,
    serialize_page,
    serialize_proposal,
)

router = APIRouter(prefix="/api/v1/wiki", tags=["wiki"])


class ReviewBody(BaseModel):
    note: str = Field(default="", max_length=MAX_REASON)


@router.get("/proposals")
def get_proposals(
    status: str | None = Query(default=None),
    session: Session = Depends(get_db),
    _: User = Depends(require("wiki:read")),
) -> dict:
    rows = list_proposals(session, status=status)
    return {"proposals": [serialize_proposal(row) for row in rows]}


@router.get("/proposals/{proposal_id}")
def get_proposal_detail(
    proposal_id: str,
    session: Session = Depends(get_db),
    _: User = Depends(require("wiki:read")),
) -> dict:
    return serialize_proposal(get_proposal(session, proposal_id))


@router.post("/proposals/{proposal_id}:approve", dependencies=[Depends(check_csrf)])
def post_approve_proposal(
    proposal_id: str,
    body: ReviewBody | None = None,
    session: Session = Depends(get_db),
    user: User = Depends(require("wiki:approve")),
) -> dict:
    proposal = get_proposal(session, proposal_id)
    page = approve_proposal(
        session,
        proposal=proposal,
        user=user,
        note=(body.note if body else "") or "",
        now=datetime.now(UTC),
    )
    return {
        "proposal": serialize_proposal(proposal),
        "page": serialize_page(page),
    }


@router.post("/proposals/{proposal_id}:reject", dependencies=[Depends(check_csrf)])
def post_reject_proposal(
    proposal_id: str,
    body: ReviewBody,
    session: Session = Depends(get_db),
    user: User = Depends(require("wiki:approve")),
) -> dict:
    proposal = get_proposal(session, proposal_id)
    reject_proposal(session, proposal=proposal, user=user, note=body.note, now=datetime.now(UTC))
    return serialize_proposal(proposal)


@router.get("/pages")
def get_pages(
    page_type: str | None = Query(default=None, alias="type"),
    session: Session = Depends(get_db),
    _: User = Depends(require("wiki:read")),
) -> dict:
    rows = list_pages(session, page_type=page_type)
    return {"pages": [serialize_page(row) for row in rows]}


@router.get("/pages/{slug}")
def get_page_detail(
    slug: str,
    session: Session = Depends(get_db),
    _: User = Depends(require("wiki:read")),
) -> dict:
    return serialize_page(get_page(session, slug))
