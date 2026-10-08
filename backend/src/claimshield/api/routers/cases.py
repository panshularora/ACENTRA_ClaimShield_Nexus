from __future__ import annotations

from datetime import UTC, datetime
from typing import Annotated

from fastapi import APIRouter, Depends, Query
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from claimshield.api.deps import check_csrf, get_current_user, get_db, require
from claimshield.auth.rbac import has_permission
from claimshield.cases.common import get_case_or_404
from claimshield.cases.decisions import MAX_EVIDENCE_REFS, MAX_REASON, record_decision, reopen_case
from claimshield.cases.network import DEFAULT_REFERRAL_TOP_N, network_pack, node_detail
from claimshield.cases.network_models import NetworkPack, NodeDetail
from claimshield.cases.workspace import (
    assign_case,
    claims_pack,
    evidence_item,
    record_rank_override,
    serialize_case,
    template_brief,
    timeline_pack,
)
from claimshield.core.errors import Forbidden
from claimshield.db.models import User

router = APIRouter(prefix="/api/v1/cases", tags=["cases"])


class DecisionBody(BaseModel):
    action: str = Field(max_length=32, description="escalate | monitor | dismiss | needs_evidence")
    reason: str = Field(max_length=MAX_REASON)
    ladder_step: str | None = Field(default=None, max_length=64)
    evidence_refs: list[Annotated[str, Field(max_length=128)]] = Field(
        default_factory=list, max_length=MAX_EVIDENCE_REFS
    )


class AssignBody(BaseModel):
    assignee_id: str | None = Field(default=None, max_length=32)


class RankOverrideBody(BaseModel):
    action: str = Field(max_length=16)
    reason: str = Field(max_length=MAX_REASON)


class ReopenBody(BaseModel):
    reason: str = Field(max_length=MAX_REASON)


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


@router.get("/{case_id}/network", response_model=NetworkPack, response_model_exclude_none=True)
def get_network(
    case_id: str,
    hops: int = Query(default=2, ge=1, le=2),
    unmask: bool = Query(default=False),
    referral_top_n: int = Query(default=DEFAULT_REFERRAL_TOP_N, ge=1, le=20),
    session: Session = Depends(get_db),
    user: User = Depends(require("case:read")),
) -> NetworkPack:
    """Subject providers plus up to two relationship hops, with typed, evidence-carrying edges."""
    case = get_case_or_404(session, case_id)
    return network_pack(session, case, user, hops=hops, unmask=unmask, referral_top_n=referral_top_n)


@router.get("/{case_id}/network/nodes/{node_id}", response_model=NodeDetail, response_model_exclude_none=True)
def get_network_node(
    case_id: str,
    node_id: str,
    unmask: bool = Query(default=False),
    session: Session = Depends(get_db),
    user: User = Depends(require("case:read")),
) -> NodeDetail:
    """Click-through for one network node: linked alerts, flagged claim lines and connections."""
    case = get_case_or_404(session, case_id)
    return node_detail(session, case, user, node_id, unmask=unmask)


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


@router.post("/{case_id}/reopen", dependencies=[Depends(check_csrf)])
def post_reopen(
    case_id: str,
    body: ReopenBody,
    session: Session = Depends(get_db),
    user: User = Depends(require("decision:approve")),
) -> dict:
    """Reopen an escalated or dismissed case so it can be decided again (manager only)."""
    case = get_case_or_404(session, case_id)
    return reopen_case(session, case=case, user=user, reason=body.reason, now=datetime.now(UTC))
