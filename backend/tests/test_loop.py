from fastapi.testclient import TestClient


def _login(client: TestClient, email: str, password: str) -> None:
    res = client.post("/api/v1/auth/login", json={"email": email, "password": password})
    assert res.status_code == 200, res.text


def _logout(client: TestClient) -> None:
    client.post("/api/v1/auth/logout")


def _load_tiny(client: TestClient) -> tuple[str, list[dict]]:
    _login(client, "manager@demo.claimshield", "demo-manager")
    res = client.post(
        "/api/v1/batches",
        json={"profile": "tiny", "seed": 7, "horizon_days": 60, "capacity_hours": 40, "run_now": True},
    )
    assert res.status_code == 200, res.text
    run_id = res.json()["run"]["run_id"]
    queue = client.get(f"/api/v1/runs/{run_id}/queue")
    assert queue.status_code == 200
    rows = queue.json()
    assert len(rows) >= 2
    return run_id, rows


def _rules_for(client: TestClient, case_id: str) -> set[str]:
    detail = client.get(f"/api/v1/cases/{case_id}")
    assert detail.status_code == 200
    return {a["rule_id"] for a in detail.json()["alerts"] if a.get("rule_id")}


def test_audit_rbac(client: TestClient) -> None:
    _load_tiny(client)
    denied_manager = client.get("/api/v1/audit")
    assert denied_manager.status_code == 403

    _logout(client)
    _login(client, "investigator@demo.claimshield", "demo-investigator")
    assert client.get("/api/v1/audit").status_code == 403
    assert client.get("/api/v1/audit/verify").status_code == 403

    _logout(client)
    _login(client, "auditor@demo.claimshield", "demo-auditor")
    ok = client.get("/api/v1/audit")
    assert ok.status_code == 200, ok.text
    body = ok.json()
    assert "events" in body
    assert "verification" in body
    assert body["verification"]["intact"] is True
    assert all("actor" in event for event in body["events"])
    assert all("password" not in str(event.get("payload", {})).lower() for event in body["events"])
    verify = client.get("/api/v1/audit/verify")
    assert verify.status_code == 200
    assert verify.json()["intact"] is True


def test_recompute_run_endpoint_and_current_run(client: TestClient) -> None:
    _run_id, _rows = _load_tiny(client)
    members_before = client.get("/api/v1/batches")
    assert members_before.status_code == 200
    n_batches = len(members_before.json())

    denied = client.post("/api/v1/auth/logout")
    assert denied.status_code == 200
    _login(client, "investigator@demo.claimshield", "demo-investigator")
    blocked = client.post("/api/v1/runs", json={"horizon_days": 90, "capacity_hours": 20})
    assert blocked.status_code == 403

    _logout(client)
    _login(client, "manager@demo.claimshield", "demo-manager")
    recomputed = client.post("/api/v1/runs", json={"horizon_days": 90, "capacity_hours": 20})
    assert recomputed.status_code == 200, recomputed.text
    body = recomputed.json()
    assert body["run_id"] != _run_id
    assert body["summary"]["capacity_hours"] == 20
    assert body["summary"]["recompute"] is True
    assert len(client.get("/api/v1/batches").json()) == n_batches

    current = client.get("/api/v1/runs/current")
    assert current.status_code == 200
    assert current.json()["run_id"] == body["run_id"]

    queue = client.get(f"/api/v1/runs/{body['run_id']}/queue")
    assert queue.status_code == 200
    row = queue.json()[0]
    assert "why_rank" in row
    assert "screening_days_left" in row
    assert row["suspicion_only"] is True
    assert "rank_factors" in row
    assert "composite" in row["rank_factors"]
    assert row["recommendation"] in {"today_queue", "gather_evidence", "tracked_backlog"}
    assert body["summary"]["ranking_policy"]["overflow_is_dismissal"] is False


def test_member_weight_and_slot_cap_change_queue(client: TestClient) -> None:
    run_id, _rows = _load_tiny(client)
    low = client.post(
        "/api/v1/runs",
        json={"horizon_days": 60, "capacity_hours": 80, "max_slots": 4, "member_weight": 0.3},
    )
    high = client.post(
        "/api/v1/runs",
        json={"horizon_days": 60, "capacity_hours": 80, "max_slots": 4, "member_weight": 2.5},
    )
    assert low.status_code == 200, low.text
    assert high.status_code == 200, high.text
    assert low.json()["run_id"] != run_id
    q_low = client.get(f"/api/v1/runs/{low.json()['run_id']}/queue").json()
    q_high = client.get(f"/api/v1/runs/{high.json()['run_id']}/queue").json()
    today_low = [r for r in q_low if r["lane"] in {"harm_priority", "selected"}]
    today_high = [r for r in q_high if r["lane"] in {"harm_priority", "selected"}]
    harm_n = sum(1 for r in q_low if r["lane"] == "harm_priority")
    assert len(today_low) <= max(4, harm_n)
    assert len(today_high) <= max(4, sum(1 for r in q_high if r["lane"] == "harm_priority"))
    overflow = [r for r in q_low if r["lane"] == "overflow"]
    assert overflow
    assert all(r["status"] == "open" for r in overflow)
    assert all(r["recommendation"] == "tracked_backlog" for r in overflow)


def test_human_override_promote_and_defer(client: TestClient) -> None:
    run_id, rows = _load_tiny(client)
    overflow = next((r for r in rows if r["lane"] == "overflow"), None)
    today = next((r for r in rows if r["lane"] in {"selected", "harm_priority"}), rows[0])
    if overflow is None:
        tight = client.post(
            "/api/v1/runs",
            json={"horizon_days": 60, "capacity_hours": 12, "max_slots": 2, "member_weight": 1.0},
        )
        assert tight.status_code == 200, tight.text
        run_id = tight.json()["run_id"]
        rows = client.get(f"/api/v1/runs/{run_id}/queue").json()
        overflow = next(r for r in rows if r["lane"] == "overflow")
        today = next(r for r in rows if r["lane"] in {"selected", "harm_priority"})

    short = client.post(
        f"/api/v1/cases/{overflow['case_id']}/rank",
        json={"action": "promote", "reason": "too short"},
    )
    assert short.status_code == 422

    promoted = client.post(
        f"/api/v1/cases/{overflow['case_id']}/rank",
        json={
            "action": "promote",
            "reason": "Wider pattern across NPIs; pull this onto today's desk for records request.",
        },
    )
    assert promoted.status_code == 200, promoted.text
    assert promoted.json()["lane"] == "selected"
    assert promoted.json()["status"] == "open"
    assert promoted.json()["recommendation"] == "today_queue"

    deferred = client.post(
        f"/api/v1/cases/{today['case_id']}/rank",
        json={
            "action": "defer",
            "reason": "Hours are tighter this week; keep the case open on the tracked backlog.",
        },
    )
    assert deferred.status_code == 200, deferred.text
    assert deferred.json()["lane"] == "overflow"
    assert deferred.json()["status"] == "open"
    assert deferred.json()["recommendation"] == "tracked_backlog"

    after = client.get(f"/api/v1/runs/{run_id}/queue").json()
    by_id = {r["case_id"]: r for r in after}
    assert by_id[overflow["case_id"]]["override"]["action"] == "promote"
    assert by_id[today["case_id"]]["lane"] == "overflow"


def test_decision_proposal_approval_and_brief_citation(client: TestClient) -> None:
    _run_id, queue = _load_tiny(client)
    source = queue[0]["case_id"]
    source_rules = _rules_for(client, source)
    other = next(
        (
            row["case_id"]
            for row in queue[1:]
            if _rules_for(client, row["case_id"]) & source_rules
        ),
        queue[1]["case_id"],
    )

    _logout(client)
    _login(client, "investigator@demo.claimshield", "demo-investigator")
    assert client.post(f"/api/v1/cases/{source}/assign", json={}).status_code == 200
    decided = client.post(
        f"/api/v1/cases/{source}/decisions",
        json={
            "action": "monitor",
            "reason": "Shared detector evidence supports monitoring this potential FWA pattern.",
        },
    )
    assert decided.status_code == 200, decided.text
    payload = decided.json()
    assert payload["audit"]["seq"] >= 1
    assert payload["audit"]["actor"]
    assert payload["audit"]["case_id"] == source
    assert payload["audit"]["reason"]
    assert payload["audit"]["chain_intact"] is True
    assert payload["proposal"]["status"] == "pending"
    assert payload["proposal"]["banner"] == "Proposed precedent — awaiting approval"
    assert payload["proposal"]["body"]["source_case"] == source
    assert payload["label"]["status"] == "pending"
    proposal_id = payload["proposal"]["proposal_id"]
    decision_id = payload["decision_id"]

    listed = client.get("/api/v1/wiki/proposals")
    assert listed.status_code == 200
    assert any(p["proposal_id"] == proposal_id for p in listed.json()["proposals"])

    _logout(client)
    _login(client, "auditor@demo.claimshield", "demo-auditor")
    audit = client.get("/api/v1/audit", params={"action": "case.decide"})
    assert audit.status_code == 200
    decide_events = [e for e in audit.json()["events"] if e["object_id"] == source]
    assert decide_events
    assert decide_events[-1]["chain_ok"] is True
    propose = client.get("/api/v1/audit", params={"action": "wiki.propose"})
    assert any(e["object_id"] == proposal_id for e in propose.json()["events"])
    assert client.post(f"/api/v1/wiki/proposals/{proposal_id}:approve", json={"note": ""}).status_code == 403

    _logout(client)
    _login(client, "manager@demo.claimshield", "demo-manager")
    reject_short = client.post(
        f"/api/v1/wiki/proposals/{proposal_id}:reject",
        json={"note": "too short"},
    )
    assert reject_short.status_code == 422

    approved = client.post(
        f"/api/v1/wiki/proposals/{proposal_id}:approve",
        json={"note": "Approved as a screening precedent for overlapping detector evidence."},
    )
    assert approved.status_code == 200, approved.text
    page = approved.json()["page"]
    assert page["status"] == "published"
    assert approved.json()["proposal"]["status"] == "approved"
    assert approved.json()["proposal"]["banner"] is None

    pages = client.get("/api/v1/wiki/pages", params={"type": "precedent"})
    assert pages.status_code == 200
    assert any(p["page_id"] == page["page_id"] for p in pages.json()["pages"])

    source_brief = client.get(f"/api/v1/cases/{source}/brief")
    assert source_brief.status_code == 200
    assert source_brief.json()["precedents"] == []

    other_brief = client.get(f"/api/v1/cases/{other}/brief")
    assert other_brief.status_code == 200
    hits = other_brief.json()["precedents"]
    shared = source_rules & _rules_for(client, other)
    if shared:
        assert hits
        hit = hits[0]
        assert hit["title"]
        assert hit["why_it_matches"]
        assert hit["matching_facts"]
        assert hit["citation"].startswith("prec:")
        assert "score" not in hit
        assert any(s["title"] == "Matched precedents" for s in other_brief.json()["sections"])
        evidence = client.get(f"/api/v1/cases/{other}/evidence/{hit['citation']}")
        assert evidence.status_code == 200
        assert evidence.json()["kind"] == "precedent"

    after = client.get(f"/api/v1/cases/{source}")
    assert after.json()["latest_label"]["status"] == "approved"
    assert after.json()["latest_proposal"]["page_id"] == page["page_id"]

    _logout(client)
    _login(client, "investigator@demo.claimshield", "demo-investigator")
    second = queue[1]["case_id"] if queue[1]["case_id"] != source else queue[2]["case_id"] if len(queue) > 2 else other
    if second == source:
        second = other
    assert client.post(f"/api/v1/cases/{second}/assign", json={}).status_code == 200
    decided2 = client.post(
        f"/api/v1/cases/{second}/decisions",
        json={
            "action": "escalate",
            "reason": "Escalate this related pattern for further SIU screening review.",
        },
    )
    assert decided2.status_code == 200, decided2.text
    assert decided2.json()["status"] == "pending_approval"
    assert decided2.json()["proposal"] is None
    alias_id = decided2.json()["decision_id"]

    _logout(client)
    _login(client, "manager@demo.claimshield", "demo-manager")
    escalated = client.post(f"/api/v1/decisions/{alias_id}:approve", json={"note": ""})
    assert escalated.status_code == 200, escalated.text
    assert escalated.json()["status"] == "escalated"
    assert escalated.json()["proposal"]["decision_id"] == alias_id

    _logout(client)
    _login(client, "analyst@demo.claimshield", "demo-analyst")
    assert client.get("/api/v1/audit").status_code == 403
    pending = client.get("/api/v1/wiki/proposals", params={"status": "pending"})
    assert pending.status_code == 200
    prop2 = next(p for p in pending.json()["proposals"] if p["decision_id"] == alias_id)
    analyst_ok = client.post(
        f"/api/v1/wiki/proposals/{prop2['proposal_id']}:approve",
        json={"note": "Analyst approval of the related screening precedent."},
    )
    assert analyst_ok.status_code == 200, analyst_ok.text

    _logout(client)
    _login(client, "manager@demo.claimshield", "demo-manager")
    already = client.post(f"/api/v1/decisions/{decision_id}:approve", json={"note": "again"})
    assert already.status_code == 409
