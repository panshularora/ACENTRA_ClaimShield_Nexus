from fastapi.testclient import TestClient


def _login(client: TestClient, email: str, password: str) -> None:
    res = client.post("/api/v1/auth/login", json={"email": email, "password": password})
    assert res.status_code == 200, res.text


def _load_tiny(client: TestClient) -> tuple[str, str]:
    _login(client, "manager@demo.claimshield", "demo-manager")
    res = client.post(
        "/api/v1/batches",
        json={"profile": "tiny", "seed": 7, "horizon_days": 60, "capacity_hours": 40, "run_now": True},
    )
    assert res.status_code == 200, res.text
    body = res.json()
    run_id = body["run"]["run_id"]
    queue = client.get(f"/api/v1/runs/{run_id}/queue")
    assert queue.status_code == 200
    case_id = queue.json()[0]["case_id"]
    return run_id, case_id


def test_workspace_pack_and_decision(client: TestClient) -> None:
    _run_id, case_id = _load_tiny(client)

    detail = client.get(f"/api/v1/cases/{case_id}")
    assert detail.status_code == 200
    case = detail.json()
    assert case["case_id"] == case_id
    assert "alerts" in case
    assert case["status"] == "open"
    assert case["primary_entity"]["provider_id"] == case["primary_entity_id"]

    brief = client.get(f"/api/v1/cases/{case_id}/brief")
    assert brief.status_code == 200
    packed = brief.json()
    assert packed["generator"] == "template"
    titles = [s["title"] for s in packed["sections"]]
    assert titles == [
        "Executive summary",
        "Why this case was surfaced",
        "Key evidence",
        "Timeline",
        "Risk / confidence",
        "Limitations",
        "Recommended human-review action",
    ]
    assert all(s["sentences"][0]["cites"] for s in packed["sections"])
    assert "potential fwa" in packed["action"].lower() or "needs more evidence" in packed["action"].lower()
    assert "is fraud" not in packed["action"].lower()

    claims = client.get(f"/api/v1/cases/{case_id}/claims")
    assert claims.status_code == 200
    rows = claims.json()["rows"]
    assert claims.json()["masked"] is True
    if rows:
        assert rows[0]["member"]["masked"] is True
        assert rows[0]["member"]["name"] is None
        item = client.get(f"/api/v1/cases/{case_id}/evidence/line:{rows[0]['line_id']}")
        assert item.status_code == 200
        assert item.json()["kind"] == "line"

    timeline = client.get(f"/api/v1/cases/{case_id}/timeline")
    assert timeline.status_code == 200
    events = timeline.json()["events"]
    assert isinstance(events, list)
    if events:
        assert events == sorted(events, key=lambda e: (e["ts"], e["kind"], e["ref"]))
        assert events[0]["ts"]

    network = client.get(f"/api/v1/cases/{case_id}/network", params={"hops": 2})
    assert network.status_code == 200
    net = network.json()
    assert net["primary_entity_id"] == case["primary_entity_id"]
    ids = {n["id"] for n in net["nodes"]}
    assert case["primary_entity_id"] in ids
    assert any(n["primary"] for n in net["nodes"])
    kinds = {n["type"] for n in net["nodes"]}
    assert "provider" in kinds
    for edge in net["edges"]:
        assert edge["source"] in ids
        assert edge["target"] in ids

    short = client.post(
        f"/api/v1/cases/{case_id}/decisions",
        json={"action": "monitor", "reason": "too short"},
    )
    assert short.status_code == 422

    bad_action = client.post(
        f"/api/v1/cases/{case_id}/decisions",
        json={"action": "fraud", "reason": "This would be an illegal automatic fraud label."},
    )
    assert bad_action.status_code == 422

    decided = client.post(
        f"/api/v1/cases/{case_id}/decisions",
        json={
            "action": "needs_evidence",
            "reason": "Need EVV visit rows and medical records before a screening recommendation.",
        },
    )
    assert decided.status_code == 200, decided.text
    payload = decided.json()
    assert payload["status"] == "needs_evidence"
    assert payload["audit"]["seq"] >= 1
    assert payload["audit"]["hash"]
    assert "not an automatic fraud label" in payload["note"].lower()

    after = client.get(f"/api/v1/cases/{case_id}")
    assert after.json()["status"] == "needs_evidence"
    assert after.json()["latest_decision"]["decision_id"] == payload["decision_id"]


def test_investigator_can_read_workspace_analyst_cannot(client: TestClient) -> None:
    _run_id, case_id = _load_tiny(client)
    client.post("/api/v1/auth/logout")
    _login(client, "investigator@demo.claimshield", "demo-investigator")
    ok = client.get(f"/api/v1/cases/{case_id}/brief")
    assert ok.status_code == 200
    client.post("/api/v1/auth/logout")
    _login(client, "analyst@demo.claimshield", "demo-analyst")
    denied = client.get(f"/api/v1/cases/{case_id}")
    assert denied.status_code == 403
