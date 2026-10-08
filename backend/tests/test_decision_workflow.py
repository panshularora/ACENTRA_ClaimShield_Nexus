"""Decision workflow: ownership, manager approval of escalations, reopen, and the audit trail."""

from fastapi.testclient import TestClient

INVESTIGATOR = ("investigator@demo.claimshield", "demo-investigator")
MANAGER = ("manager@demo.claimshield", "demo-manager")
ADMIN = ("admin@demo.claimshield", "demo-admin")
AUDITOR = ("auditor@demo.claimshield", "demo-auditor")
REASON = "Flagged lines and peer comparison support this screening step for review."


def _as(client: TestClient, who: tuple[str, str]) -> None:
    client.post("/api/v1/auth/logout")
    res = client.post("/api/v1/auth/login", json={"email": who[0], "password": who[1]})
    assert res.status_code == 200, res.text


def _queue(client: TestClient) -> list[dict]:
    _as(client, MANAGER)
    res = client.post(
        "/api/v1/batches",
        json={"profile": "tiny", "seed": 7, "horizon_days": 60, "capacity_hours": 40, "run_now": True},
    )
    assert res.status_code == 200, res.text
    rows = client.get(f"/api/v1/runs/{res.json()['run']['run_id']}/queue").json()
    assert len(rows) >= 3
    return rows


def _decide(client: TestClient, case_id: str, action: str, **extra: object):
    return client.post(f"/api/v1/cases/{case_id}/decisions", json={"action": action, "reason": REASON, **extra})


def test_escalation_needs_owner_then_manager_approval(client: TestClient) -> None:
    rows = _queue(client)
    case_id = rows[0]["case_id"]

    _as(client, INVESTIGATOR)
    unowned = _decide(client, case_id, "escalate")
    assert unowned.status_code == 403
    assert "ownership" in unowned.json()["detail"]
    detail = client.get(f"/api/v1/cases/{case_id}").json()
    assert detail["allowed_actions"] == []
    assert detail["decision_blocked_reason"]
    escalate_steps = {o["step"]: o for o in detail["decision_options"]["escalate"]}
    assert escalate_steps["state_pi_referral"]["default"] is True
    assert "mfcu_referral" not in escalate_steps
    assert all(o["requires_approval"] for o in escalate_steps.values())
    assert "state agency decision" in escalate_steps["payment_suspension_recommend"]["label"]

    assert client.post(f"/api/v1/cases/{case_id}/assign", json={}).status_code == 200
    assert set(client.get(f"/api/v1/cases/{case_id}").json()["allowed_actions"]) == {
        "escalate",
        "monitor",
        "dismiss",
        "needs_evidence",
    }
    wrong_step = _decide(client, case_id, "escalate", ladder_step="education_letter")
    assert wrong_step.status_code == 422

    pending = _decide(client, case_id, "escalate")
    assert pending.status_code == 200, pending.text
    body = pending.json()
    assert body["status"] == "pending_approval"
    assert body["decision_status"] == "pending_approval"
    assert body["ladder_step"] == "state_pi_referral"
    assert body["approved_by"] is None
    assert body["proposal"] is None
    decision_id = body["decision_id"]

    # While pending, nobody decides again and the investigator cannot approve.
    assert _decide(client, case_id, "dismiss").status_code == 409
    assert client.post(f"/api/v1/decisions/{decision_id}:approve", json={}).status_code == 403

    _as(client, MANAGER)
    detail = client.get(f"/api/v1/cases/{case_id}").json()
    assert detail["status"] == "pending_approval"
    assert detail["pending_decision"]["decision_id"] == decision_id
    assert {"approve", "reject"} <= set(detail["allowed_actions"])
    approved = client.post(f"/api/v1/decisions/{decision_id}:approve", json={"note": "Basis reviewed."})
    assert approved.status_code == 200, approved.text
    assert approved.json()["status"] == "escalated"
    decision = approved.json()["decision"]
    assert decision["status"] == "approved"
    assert decision["approved_by"]
    assert decision["approved_at"]
    assert approved.json()["proposal"]["status"] == "pending"
    assert client.post(f"/api/v1/decisions/{decision_id}:approve", json={}).status_code == 409

    # Closed: a new decision needs a reopen, and only a manager may reopen.
    assert _decide(client, case_id, "monitor").status_code == 409
    _as(client, INVESTIGATOR)
    assert client.post(f"/api/v1/cases/{case_id}/reopen", json={"reason": REASON}).status_code == 403
    _as(client, MANAGER)
    assert client.post(f"/api/v1/cases/{case_id}/reopen", json={"reason": "short"}).status_code == 422
    reopened = client.post(f"/api/v1/cases/{case_id}/reopen", json={"reason": REASON})
    assert reopened.status_code == 200, reopened.text
    assert reopened.json()["status"] == "open"
    assert reopened.json()["prior_status"] == "escalated"
    assert _decide(client, case_id, "monitor").status_code == 200

    _as(client, AUDITOR)
    for action in ("case.decide", "case.decision.approve", "case.reopen"):
        events = client.get("/api/v1/audit", params={"action": action}).json()["events"]
        assert any(e["object_id"] == case_id for e in events), action


def test_suspension_recommendation_reject_and_follow_up(client: TestClient) -> None:
    rows = _queue(client)
    case_id, other_id = rows[1]["case_id"], rows[2]["case_id"]

    # A manager may decide without ownership but cannot approve their own escalation.
    own = _decide(client, case_id, "escalate", ladder_step="payment_suspension_recommend")
    assert own.status_code == 200, own.text
    own_id = own.json()["decision_id"]
    assert client.post(f"/api/v1/decisions/{own_id}:approve", json={}).status_code == 403

    _as(client, ADMIN)
    no_basis = client.post(f"/api/v1/decisions/{own_id}:approve", json={"note": "ok"})
    assert no_basis.status_code == 422
    assert client.post(f"/api/v1/decisions/{own_id}:reject", json={"note": "short"}).status_code == 422
    rejected = client.post(
        f"/api/v1/decisions/{own_id}:reject",
        json={"note": "Evidence does not yet meet a credible-allegation standard; gather records."},
    )
    assert rejected.status_code == 200, rejected.text
    assert rejected.json()["status"] == "open"
    assert rejected.json()["decision"]["status"] == "rejected"

    # needs_evidence keeps the case decidable; the follow-up decision is accepted.
    _as(client, INVESTIGATOR)
    assert client.post(f"/api/v1/cases/{case_id}/assign", json={}).status_code == 200
    first = _decide(client, case_id, "needs_evidence")
    assert first.status_code == 200, first.text
    assert first.json()["status"] == "needs_evidence"
    follow_up = _decide(client, case_id, "dismiss")
    assert follow_up.status_code == 200, follow_up.text
    assert follow_up.json()["status"] == "dismissed"

    # Segregation of duties on precedents: the manager cannot publish one from their own decision.
    _as(client, MANAGER)
    mine = _decide(client, rows[0]["case_id"], "monitor")
    assert mine.status_code == 200, mine.text
    proposal_id = mine.json()["proposal"]["proposal_id"]
    note = {"note": "Publishing my own precedent should be refused by the workflow."}
    assert client.post(f"/api/v1/wiki/proposals/{proposal_id}:approve", json=note).status_code == 403
    _as(client, ADMIN)
    assert client.post(f"/api/v1/wiki/proposals/{proposal_id}:approve", json=note).status_code == 200

    # Another investigator's case is off limits; length limits are enforced.
    _as(client, MANAGER)
    assert client.post(f"/api/v1/cases/{other_id}/assign", json={}).status_code == 200
    _as(client, INVESTIGATOR)
    assert _decide(client, other_id, "monitor").status_code == 403
    assert client.post(f"/api/v1/cases/{other_id}/assign", json={}).status_code == 403
    too_long = client.post(
        f"/api/v1/cases/{other_id}/decisions", json={"action": "monitor", "reason": "x" * 4001}
    )
    assert too_long.status_code == 422
