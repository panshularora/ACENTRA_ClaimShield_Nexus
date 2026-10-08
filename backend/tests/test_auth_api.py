from fastapi.testclient import TestClient


def test_healthz(client: TestClient) -> None:
    res = client.get("/healthz")
    assert res.status_code == 200
    assert res.json()["status"] == "ok"


def test_login_me_and_logout(client: TestClient) -> None:
    bad = client.post(
        "/api/v1/auth/login",
        json={"email": "investigator@demo.claimshield", "password": "wrong"},
    )
    assert bad.status_code == 401

    res = client.post(
        "/api/v1/auth/login",
        json={"email": "investigator@demo.claimshield", "password": "demo-investigator"},
    )
    assert res.status_code == 200
    body = res.json()
    assert body["role"] == "investigator"
    assert "case:decide" in body["permissions"]
    assert "cs_access" in res.cookies

    me = client.get("/api/v1/auth/me")
    assert me.status_code == 200
    assert me.json()["email"] == "investigator@demo.claimshield"

    out = client.post("/api/v1/auth/logout")
    assert out.status_code == 200
    me2 = client.get("/api/v1/auth/me")
    assert me2.status_code == 401


def test_refresh_rotation_and_reuse(client: TestClient) -> None:
    client.post(
        "/api/v1/auth/login",
        json={"email": "manager@demo.claimshield", "password": "demo-manager"},
    )
    first_refresh = client.cookies.get("cs_refresh")
    assert first_refresh

    rotated = client.post("/api/v1/auth/refresh")
    assert rotated.status_code == 200
    second = client.cookies.get("cs_refresh")
    assert second
    assert second != first_refresh

    # replay of the old refresh token must revoke
    client.cookies.set("cs_refresh", first_refresh)
    replay = client.post("/api/v1/auth/refresh")
    assert replay.status_code == 401


def test_investigator_cannot_load_batch(client: TestClient) -> None:
    client.post(
        "/api/v1/auth/login",
        json={"email": "investigator@demo.claimshield", "password": "demo-investigator"},
    )
    res = client.post("/api/v1/batches", json={"profile": "tiny", "seed": 7, "run_now": False})
    assert res.status_code == 403
