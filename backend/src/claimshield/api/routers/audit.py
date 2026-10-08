from __future__ import annotations

from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from claimshield.api.deps import get_db, require
from claimshield.audit.service import get_event, public_log, verify_stored_chain
from claimshield.db.models import User

router = APIRouter(prefix="/api/v1", tags=["audit"])


@router.get("/audit")
def list_audit(
    actor: str | None = Query(default=None),
    action: str | None = Query(default=None),
    from_ts: str | None = Query(default=None, alias="from"),
    to_ts: str | None = Query(default=None, alias="to"),
    session: Session = Depends(get_db),
    _: User = Depends(require("audit:read")),
) -> dict:
    return public_log(session, actor=actor, action=action, from_ts=from_ts, to_ts=to_ts)


@router.get("/audit/verify")
def verify_audit(
    session: Session = Depends(get_db),
    _: User = Depends(require("audit:read")),
) -> dict:
    verify_stored_chain(session)
    pack = public_log(session)
    return pack["verification"]


@router.get("/audit/{seq}")
def get_audit_event(
    seq: int,
    session: Session = Depends(get_db),
    _: User = Depends(require("audit:read")),
) -> dict:
    return get_event(session, seq)
