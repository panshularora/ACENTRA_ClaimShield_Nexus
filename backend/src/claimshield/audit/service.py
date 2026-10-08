from __future__ import annotations

from datetime import UTC, datetime
from typing import Any

from sqlalchemy import select
from sqlalchemy.orm import Session

from claimshield.audit.chain import chain_hash, verify_chain
from claimshield.core.clock import as_utc, canonical_iso
from claimshield.core.errors import Conflict, NotFound
from claimshield.db.models import AuditEvent, User

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


REDACT_FRAGMENTS = ("password", "token", "secret", "cookie", "authorization", "api_key", "signing")


def serialize_event_row(event: AuditEvent) -> dict[str, Any]:
    return {
        "seq": event.seq,
        "ts": canonical_iso(event.ts) if hasattr(event.ts, "isoformat") else str(event.ts),
        "actor_id": event.actor_id,
        "role": event.role,
        "action": event.action,
        "object_type": event.object_type,
        "object_id": event.object_id,
        "payload": event.payload or {},
        "prev_hash": event.prev_hash,
        "hash": event.hash,
    }


def sanitize_payload(payload: dict[str, Any] | None) -> dict[str, Any]:
    out: dict[str, Any] = {}
    for key, value in (payload or {}).items():
        lowered = str(key).lower()
        if any(frag in lowered for frag in REDACT_FRAGMENTS):
            out[key] = "[redacted]"
        else:
            out[key] = value
    return out


def list_events(session: Session) -> list[dict[str, Any]]:
    events = session.execute(select(AuditEvent).order_by(AuditEvent.seq.asc())).scalars().all()
    return [serialize_event_row(e) for e in events]


def chain_status(session: Session) -> dict[str, Any]:
    serialised = list_events(session)
    intact = verify_chain(serialised)
    last = serialised[-1] if serialised else None
    return {
        "intact": intact,
        "last_seq": last["seq"] if last else 0,
        "last_hash": last["hash"] if last else None,
        "n_events": len(serialised),
    }


def annotate_chain(serialised: list[dict[str, Any]]) -> list[dict[str, Any]]:
    previous = GENESIS
    out: list[dict[str, Any]] = []
    broken = False
    for row in serialised:
        expected = chain_hash(previous, row)
        ok = (not broken) and row.get("prev_hash") == previous and row.get("hash") == expected
        if not ok:
            broken = True
        public = dict(row)
        public["payload"] = sanitize_payload(row.get("payload") if isinstance(row.get("payload"), dict) else {})
        public["chain_ok"] = ok
        out.append(public)
        previous = row.get("hash") or previous
    return out


def verify_stored_chain(session: Session) -> bool:
    ok = verify_chain(list_events(session))
    if not ok:
        raise Conflict("audit chain verification failed")
    return True


def _actor_names(session: Session) -> dict[str, str]:
    users = session.execute(select(User)).scalars().all()
    return {u.id: u.display_name for u in users}


def public_event(row: dict[str, Any], names: dict[str, str]) -> dict[str, Any]:
    actor_id = row.get("actor_id")
    return {
        "seq": row["seq"],
        "ts": row["ts"],
        "actor_id": actor_id,
        "actor": (names.get(actor_id) if actor_id else None) or ("system" if not actor_id else "unknown"),
        "role": row["role"],
        "action": row["action"],
        "object_type": row["object_type"],
        "object_id": row["object_id"],
        "payload": row.get("payload") or {},
        "chain_ok": row.get("chain_ok"),
        "hash": row.get("hash"),
        "prev_hash": row.get("prev_hash"),
    }


def public_log(
    session: Session,
    *,
    actor: str | None = None,
    action: str | None = None,
    from_ts: str | None = None,
    to_ts: str | None = None,
) -> dict[str, Any]:
    names = _actor_names(session)
    events = [public_event(row, names) for row in annotate_chain(list_events(session))]
    filtered: list[dict[str, Any]] = []
    for event in events:
        if actor:
            needle = actor.lower()
            actor_id = (event.get("actor_id") or "").lower()
            actor_name = (event.get("actor") or "").lower()
            if needle not in actor_id and needle not in actor_name:
                continue
        if action and event.get("action") != action:
            continue
        ts = event.get("ts") or ""
        if from_ts and ts < from_ts:
            continue
        if to_ts and ts > to_ts:
            continue
        filtered.append(event)
    return {"events": filtered, "verification": chain_status(session)}


def get_event(session: Session, seq: int) -> dict[str, Any]:
    pack = public_log(session)
    for event in pack["events"]:
        if event["seq"] == seq:
            return event
    raise NotFound("audit event not found")
