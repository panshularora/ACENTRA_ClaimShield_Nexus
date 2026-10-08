from __future__ import annotations

from datetime import UTC, datetime
from typing import Any

from sqlalchemy import select
from sqlalchemy.orm import Session

from claimshield.audit.chain import chain_hash, verify_chain
from claimshield.core.clock import as_utc, canonical_iso
from claimshield.core.errors import Conflict
from claimshield.db.models import AuditEvent

GENESIS = "0" * 64


def append_event(
    session: Session,
    *,
    actor_id: str | None,
    role: str,
    action: str,
    object_type: str,
    object_id: str,
    payload: dict[str, Any] | None = None,
    ts: datetime | None = None,
) -> AuditEvent:
    last = session.execute(select(AuditEvent).order_by(AuditEvent.seq.desc()).limit(1)).scalar_one_or_none()
    prev = last.hash if last else GENESIS
    next_seq = (last.seq + 1) if last else 1
    instant = as_utc(ts or datetime.now(UTC)).replace(microsecond=0)
    iso = canonical_iso(instant)
    row = {
        "seq": next_seq,
        "ts": iso,
        "actor_id": actor_id,
        "role": role,
        "action": action,
        "object_type": object_type,
        "object_id": object_id,
        "payload": payload or {},
    }
    digest = chain_hash(prev, row)
    event = AuditEvent(
        ts=instant,
        actor_id=actor_id,
        role=role,
        action=action,
        object_type=object_type,
        object_id=object_id,
        payload=payload or {},
        prev_hash=prev,
        hash=digest,
    )
    session.add(event)
    session.flush()
    return event


def verify_stored_chain(session: Session) -> bool:
    events = session.execute(select(AuditEvent).order_by(AuditEvent.seq.asc())).scalars().all()
    serialised = [
        {
            "seq": e.seq,
            "ts": canonical_iso(e.ts) if hasattr(e.ts, "isoformat") else str(e.ts),
            "actor_id": e.actor_id,
            "role": e.role,
            "action": e.action,
            "object_type": e.object_type,
            "object_id": e.object_id,
            "payload": e.payload,
            "prev_hash": e.prev_hash,
            "hash": e.hash,
        }
        for e in events
    ]
    ok = verify_chain(serialised)
    if not ok:
        raise Conflict("audit chain verification failed")
    return True
