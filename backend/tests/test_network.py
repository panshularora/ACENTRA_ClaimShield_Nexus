"""Case network API: typed linkage, evidence on edges, scoped neighbourhood, click-through."""

from __future__ import annotations

from collections.abc import Iterator
from typing import Any

import pytest
from fastapi.testclient import TestClient

from claimshield.api.deps import reset_engine
from claimshield.cases.network import MAX_MEMBERS, MAX_PROVIDERS
from claimshield.core.config import get_settings


@pytest.fixture(scope="module")
def loaded(tmp_path_factory: pytest.TempPathFactory) -> Iterator[tuple[TestClient, list[dict[str, Any]]]]:
    db = tmp_path_factory.mktemp("network") / "network.db"
    with pytest.MonkeyPatch.context() as mp:
        mp.setenv("CLAIMSHIELD_DATABASE_URL", f"sqlite+pysqlite:///{db.as_posix()}")
        mp.setenv("CLAIMSHIELD_JWT_SIGNING_KEY", "test-signing-key-for-network-tests-32b")
        mp.setenv("CLAIMSHIELD_COOKIE_SECURE", "false")
        mp.setenv("CLAIMSHIELD_DEMO_MODE", "true")
        get_settings.cache_clear()
        reset_engine()
        from claimshield.api.main import create_app

        with TestClient(create_app()) as client:
            login = client.post(
                "/api/v1/auth/login", json={"email": "manager@demo.claimshield", "password": "demo-manager"}
            )
            client.headers["X-CSRF-Token"] = login.json()["csrf_token"]
            res = client.post("/api/v1/batches", json={"profile": "tiny", "seed": 7, "run_now": True})
            assert res.status_code == 200, res.text
            queue = client.get(f"/api/v1/runs/{res.json()['run']['run_id']}/queue").json()
            yield client, queue
        reset_engine()
        get_settings.cache_clear()


def _network(client: TestClient, case_id: str, **params: Any) -> dict[str, Any]:
    res = client.get(f"/api/v1/cases/{case_id}/network", params=params)
    assert res.status_code == 200, res.text
    body: dict[str, Any] = res.json()
    return body


def _ring_case(client: TestClient, queue: list[dict[str, Any]], *, edge_kind: str = "shared_contact") -> dict[str, Any]:
    for row in queue:
        detail: dict[str, Any] = client.get(f"/api/v1/cases/{row['case_id']}").json()
        rings = [a for a in detail["alerts"] if a["kind"] == "identity_ring"]
        if any(edge_kind in a["evidence"]["edge_kinds"] for a in rings):
            return detail
    raise AssertionError(f"seed 7 should contain an identity ring linked by {edge_kind}")


def test_every_network_is_scoped_and_consistent(loaded: tuple[TestClient, list[dict[str, Any]]]) -> None:
    client, queue = loaded
    for row in queue:
        net = _network(client, row["case_id"])
        assert net["schema_version"] == 2
        ids = {n["id"] for n in net["nodes"]}
        assert len(ids) == len(net["nodes"])
        providers = [n for n in net["nodes"] if n["type"] == "provider"]
        assert len(providers) <= MAX_PROVIDERS
        assert sum(1 for n in net["nodes"] if n["type"] == "member") <= MAX_MEMBERS
        # A one-provider case stays a neighbourhood, not most of the 47-provider extract.
        if len(net["subject_ids"]) == 1:
            assert len(providers) <= 16
        assert set(net["subject_ids"]) <= ids
        assert all(n["hop"] == 0 for n in net["nodes"] if n["is_subject"])
        assert all(n["hop"] <= 2 for n in net["nodes"])
        for edge in net["edges"]:
            assert edge["source"] in ids and edge["target"] in ids
            assert edge["kind"] != "shared_location", "addresses are hub nodes, not cliques"
            assert 0 < edge["weight"] <= 1
            assert edge["id"] == f"{edge['kind']}:{edge['source']}:{edge['target']}"
        referrals = [e for e in net["edges"] if e["kind"] == "referral"]
        assert all(e["directed"] and e["count"] >= 1 for e in referrals)
        for subject in net["subject_ids"]:
            partners = {e["target"] if e["source"] == subject else e["source"] for e in referrals if subject in (e["source"], e["target"])}
            assert len(partners - set(net["subject_ids"])) <= net["limits"]["referral_top_n"]


def test_ring_case_draws_its_evidence(loaded: tuple[TestClient, list[dict[str, Any]]]) -> None:
    client, queue = loaded
    case = _ring_case(client, queue)
    ring = next(a for a in case["alerts"] if a["kind"] == "identity_ring")
    net = _network(client, case["case_id"])
    nodes = {n["id"]: n for n in net["nodes"]}
    kinds = {e["kind"] for e in net["edges"]}
    assert "shared_contact" in kinds
    for kind in ring["evidence"]["edge_kinds"]:
        edge_kind = "owns" if kind == "shared_owner" else kind
        backing = [e for e in net["edges"] if e["kind"] == edge_kind and ring["alert_id"] in e["evidence"]["alert_ids"]]
        assert backing, f"no {edge_kind} edge carries the ring alert"
        assert all(e["in_case"] for e in backing)
    contact = next(e for e in net["edges"] if e["kind"] == "shared_contact")
    attribute = contact["evidence"]["attribute"]
    assert "••••" in attribute["value_masked"]
    assert attribute["kind"] in {"phone", "email", "bank_token"}
    for pid in ring["evidence"]["peer_ids"]:
        assert nodes[pid]["is_subject"] and nodes[pid]["in_case"]
        assert ring["alert_id"] in nodes[pid]["alert_ids"]
        assert nodes[pid]["n_flagged_lines"] >= 1 and nodes[pid]["flagged_dollars"] > 0
    owners = [n for n in net["nodes"] if n["type"] == "owner" and ring["alert_id"] in n["alert_ids"]]
    assert owners


def test_shared_address_is_a_hub(loaded: tuple[TestClient, list[dict[str, Any]]]) -> None:
    client, queue = loaded
    found = False
    for row in queue:
        net = _network(client, row["case_id"])
        for hub in (n for n in net["nodes"] if n["type"] == "address"):
            spokes = [e for e in net["edges"] if e["target"] == hub["id"]]
            assert len(spokes) >= 2
            assert all(e["kind"] == "located_at" and e["directed"] for e in spokes)
            found = True
    assert found


def test_members_are_masked_without_unmask(loaded: tuple[TestClient, list[dict[str, Any]]]) -> None:
    client, queue = loaded
    net = _network(client, queue[0]["case_id"])
    assert net["masked"] is True
    members = [n for n in net["nodes"] if n["type"] == "member"]
    assert members
    assert all(n["masked"] is True and n["label"].startswith("Member ·") for n in members)


def test_node_click_through(loaded: tuple[TestClient, list[dict[str, Any]]]) -> None:
    client, queue = loaded
    case = _ring_case(client, queue)
    net = _network(client, case["case_id"])
    primary = next(n for n in net["nodes"] if n["primary"])
    res = client.get(primary["detail_path"])
    assert res.status_code == 200, res.text
    detail = res.json()
    assert detail["node"]["id"] == primary["id"]
    assert {a["alert_id"] for a in detail["alerts"]} == set(primary["alert_ids"])
    assert detail["claim_lines"]
    assert all(primary["id"] in {r["billing_provider_id"], r["rendering_provider_id"], r["ordering_provider_id"]} for r in detail["claim_lines"])
    assert detail["connections"]
    assert detail["profile"]["provider_id"] == primary["id"]

    owner = next(n for n in net["nodes"] if n["type"] == "owner")
    owner_detail = client.get(owner["detail_path"]).json()
    assert owner_detail["profile"]["providers"]

    member = next(n for n in net["nodes"] if n["type"] == "member")
    member_detail = client.get(member["detail_path"]).json()
    assert member_detail["claim_lines"]
    assert all(r["member"]["masked"] for r in member_detail["claim_lines"])

    outside = client.get(f"/api/v1/cases/{case['case_id']}/network/nodes/PRV-NOT-IN-CASE")
    assert outside.status_code == 404
    evidence = client.get(f"/api/v1/cases/{case['case_id']}/evidence/node:{primary['id']}")
    assert evidence.status_code == 200
    assert evidence.json()["kind"] == "node"


def test_hops_one_is_smaller(loaded: tuple[TestClient, list[dict[str, Any]]]) -> None:
    client, queue = loaded
    case = _ring_case(client, queue)
    one = _network(client, case["case_id"], hops=1)
    two = _network(client, case["case_id"], hops=2)
    assert len(one["nodes"]) <= len(two["nodes"])
    assert all(n["hop"] <= 1 for n in one["nodes"])
