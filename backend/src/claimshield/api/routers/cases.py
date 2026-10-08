from __future__ import annotations

from datetime import UTC, datetime

from fastapi import APIRouter, Depends, Query
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session


from claimshield.api.deps import check_csrf, get_current_user, get_db, require
from claimshield.auth.rbac import has_permission
from claimshield.cases.workspace import (
    assign_case,
    claims_pack,
    evidence_item,
    get_case_or_404,
    network_pack,
    record_decision,
    record_rank_override,
    serialize_case,
    template_brief,
    timeline_pack,
)
from claimshield.core.errors import Forbidden
from claimshield.db.models import User

router = APIRouter(prefix="/api/v1/cases", tags=["cases"])


class DecisionBody(BaseModel):
    action: str
    reason: str
    ladder_step: str | None = None
    evidence_refs: list[str] = Field(default_factory=list)


class AssignBody(BaseModel):
    assignee_id: str | None = None


class RankOverrideBody(BaseModel):
    action: str
    reason: str


@router.get("/{case_id}")
def get_case(
    case_id: str,
    session: Session = Depends(get_db),
    user: User = Depends(require("case:read")),
) -> dict:
    case = get_case_or_404(session, case_id)
    return serialize_case(session, case, user)


@router.get("/{case_id}/brief")
def get_brief(
    case_id: str,
    session: Session = Depends(get_db),
    user: User = Depends(require("case:read")),
) -> dict:
    case = get_case_or_404(session, case_id)
    return template_brief(session, case, user)


@router.get("/{case_id}/claims")
def get_claims(
    case_id: str,
    unmask: bool = Query(default=False),
    session: Session = Depends(get_db),
    user: User = Depends(require("case:read")),
) -> dict:
    case = get_case_or_404(session, case_id)
    return claims_pack(session, case, user, unmask=unmask)


@router.get("/{case_id}/timeline")
def get_timeline(
    case_id: str,
    unmask: bool = Query(default=False),
    session: Session = Depends(get_db),
    user: User = Depends(require("case:read")),
) -> dict:
    case = get_case_or_404(session, case_id)
    return timeline_pack(session, case, user, unmask=unmask)


@router.get("/{case_id}/network")
def get_network(
    case_id: str,
    hops: int = Query(default=2, ge=1, le=2),
    unmask: bool = Query(default=False),
    session: Session = Depends(get_db),
    user: User = Depends(require("case:read")),
) -> dict:
    case = get_case_or_404(session, case_id)
    return network_pack(session, case, user, hops=hops, unmask=unmask)


@router.get("/{case_id}/evidence/{item_id}")
def get_evidence(
    case_id: str,
    item_id: str,
    session: Session = Depends(get_db),
    user: User = Depends(require("case:read")),
) -> dict:
    case = get_case_or_404(session, case_id)
    return evidence_item(session, case, item_id, user)


@router.post("/{case_id}/assign", dependencies=[Depends(check_csrf)])
def post_assign(
    case_id: str,
    body: AssignBody,
    session: Session = Depends(get_db),
    user: User = Depends(require("case:assign")),
) -> dict:
    case = get_case_or_404(session, case_id)
    return assign_case(
        session,
        case=case,
        user=user,
        assignee_id=body.assignee_id or user.id,
        now=datetime.now(UTC),
    )


@router.post("/{case_id}/rank", dependencies=[Depends(check_csrf)])
def post_rank_override(
    case_id: str,
    body: RankOverrideBody,
    session: Session = Depends(get_db),
    user: User = Depends(get_current_user),
) -> dict:
    if not (
        has_permission(user.role, "queue:configure")
        or has_permission(user.role, "case:decide")
        or has_permission(user.role, "admin:*")
    ):
        raise Forbidden("role cannot override queue rank")
    case = get_case_or_404(session, case_id)
    return record_rank_override(
        session,
        case=case,
        user=user,
        action=body.action,
        reason=body.reason,
        now=datetime.now(UTC),
    )


@router.post("/{case_id}/decisions", dependencies=[Depends(check_csrf)])
def post_decision(
    case_id: str,
    body: DecisionBody,
    session: Session = Depends(get_db),
    user: User = Depends(require("case:decide")),
) -> dict:
    case = get_case_or_404(session, case_id)
    return record_decision(
        session,
        case=case,
        user=user,
        action=body.action,
        reason=body.reason,
        ladder_step=body.ladder_step,
        evidence_refs=body.evidence_refs,
        now=datetime.now(UTC),
    )
