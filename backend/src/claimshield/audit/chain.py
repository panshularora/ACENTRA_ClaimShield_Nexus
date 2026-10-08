from __future__ import annotations

import hashlib
import json
from collections.abc import Mapping, Sequence
from typing import Any


def _canonical(row: Mapping[str, Any]) -> str:
    payload = {
        "seq": row["seq"],
        "ts": row["ts"],
        "actor_id": row["actor_id"],
        "role": row["role"],
        "action": row["action"],
        "object_type": row["object_type"],
        "object_id": row["object_id"],
        "payload": row.get("payload") or {},
        "prev_hash": row.get("prev_hash", ""),
    }
    return json.dumps(payload, sort_keys=True, separators=(",", ":"), default=str)


def chain_hash(prev_hash: str, row: Mapping[str, Any]) -> str:
    material = prev_hash + _canonical({**row, "prev_hash": prev_hash})
    return hashlib.sha256(material.encode("utf-8")).hexdigest()


def verify_chain(events: Sequence[Mapping[str, Any]], *, genesis: str | None = None) -> bool:
    previous = genesis if genesis is not None else "0" * 64
    for event in events:
        expected_prev = event.get("prev_hash")
        if expected_prev != previous:
            return False
        recomputed = chain_hash(previous, event)
        if recomputed != event.get("hash"):
            return False
        previous = recomputed
    return True
