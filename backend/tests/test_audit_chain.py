import json

from claimshield.audit.chain import chain_hash, verify_chain


def test_chain_hash_links_to_previous_and_tamper_breaks_verify() -> None:
    genesis = "0" * 64
    row1 = {
        "seq": 1,
        "ts": "2026-01-01T00:00:00+00:00",
        "actor_id": "USR-1",
        "role": "manager",
        "action": "batch.load",
        "object_type": "batch",
        "object_id": "BAT-1",
        "payload": {"rows": 10},
    }
    h1 = chain_hash(genesis, row1)
    row2 = {
        "seq": 2,
        "ts": "2026-01-01T00:00:01+00:00",
        "actor_id": "USR-1",
        "role": "manager",
        "action": "run.start",
        "object_type": "run",
        "object_id": "RUN-1",
        "payload": {"horizon_days": 60},
    }
    h2 = chain_hash(h1, row2)
    events = [
        {**row1, "prev_hash": genesis, "hash": h1},
        {**row2, "prev_hash": h1, "hash": h2},
    ]
    assert verify_chain(events) is True

    tampered = json.loads(json.dumps(events))
    tampered[0]["payload"]["rows"] = 999
    assert verify_chain(tampered) is False
