from __future__ import annotations

from fastapi.testclient import TestClient

RISK_KEYS = {
    "p_confirm",
    "f30",
    "f60",
    "f90",
    "risk_30",
    "risk_60",
    "risk_90",
    "score_kind",
    "model_version",
    "calibrated",
    "risk_as_of",
    "risk_subject",
    "monthly_hazards",
    "risk_factors",
    "p_confirm_factors",
}


def _login(client: TestClient, email: str, password: str) -> None:
    res = client.post("/api/v1/auth/login", json={"email": email, "password": password})
    assert res.status_code == 200, res.text


def test_queue_case_and_model_endpoints_expose_model_risk(client: TestClient) -> None:
    _login(client, "manager@demo.claimshield", "demo-manager")
    res = client.post("/api/v1/batches", json={"profile": "tiny", "seed": 7, "run_now": True})
    assert res.status_code == 200, res.text
    run = res.json()["run"]
    assert run["risk_model"]["score_kind"] == "trained_model"
    rows = client.get(f"/api/v1/runs/{run['run_id']}/queue").json()
    assert rows
    for row in rows:
        assert set(row) >= RISK_KEYS, RISK_KEYS - set(row)
        assert row["score_kind"] == "trained_model"
        assert row["calibrated"] is True
        assert row["risk_30"] == row["f30"]
        assert row["model_version"] == run["risk_model"]["model_version"]

    detail = client.get(f"/api/v1/cases/{rows[0]['case_id']}").json()
    assert set(detail) >= RISK_KEYS
    assert detail["p_confirm_factors"]

    brief = client.get(f"/api/v1/cases/{rows[0]['case_id']}/brief").json()
    text = " ".join(s["text"] for sec in brief["sections"] for s in sec["sentences"])
    assert "trained on synthetic data" in text

    model = client.get("/api/v1/models/risk")
    assert model.status_code == 200
    body = model.json()
    assert body["model_version"] == run["risk_model"]["model_version"]
    assert body["metrics"]["hazard"]["90d"]["model"]["pr_auc"] is not None
    assert body["labels"]["hazard"]


def test_model_card_endpoint_needs_model_read(client: TestClient) -> None:
    _login(client, "investigator@demo.claimshield", "demo-investigator")
    assert client.get("/api/v1/models/risk").status_code == 403
