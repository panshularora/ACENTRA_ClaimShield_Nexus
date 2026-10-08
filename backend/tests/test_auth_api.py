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

    # replay of the old refresh token must revoke, and the revocation must survive the 401
    client.cookies.set("cs_refresh", first_refresh)
    replay = client.post("/api/v1/auth/refresh")
    assert replay.status_code == 401
    client.cookies.clear()
    client.cookies.set("cs_refresh", second)
    after_reuse = client.post("/api/v1/auth/refresh")
    assert after_reuse.status_code == 401
    assert after_reuse.json()["detail"] == "invalid refresh token"


def test_investigator_cannot_load_batch(client: TestClient) -> None:
    client.post(
        "/api/v1/auth/login",
        json={"email": "investigator@demo.claimshield", "password": "demo-investigator"},
    )
    res = client.post("/api/v1/batches", json={"profile": "tiny", "seed": 7, "run_now": False})
    assert res.status_code == 403


def _login(client: TestClient, email: str, password: str):
    return client.post("/api/v1/auth/login", json={"email": email, "password": password})


def test_csrf_header_required_for_cookie_writes(client: TestClient) -> None:
    assert _login(client, "investigator@demo.claimshield", "demo-investigator").status_code == 200
    csrf = client.cookies.get("cs_csrf")
    client.event_hooks["request"] = []  # stop echoing the CSRF cookie like the web client does
    missing = client.post("/api/v1/auth/logout")
    assert missing.status_code == 401
    assert missing.json()["detail"] == "csrf check failed"
    wrong = client.post("/api/v1/auth/logout", headers={"X-CSRF-Token": "not-the-cookie"})
    assert wrong.status_code == 401
    ok = client.post("/api/v1/auth/logout", headers={"X-CSRF-Token": csrf})
    assert ok.status_code == 200


def test_failed_login_is_audited(client: TestClient) -> None:
    assert _login(client, "investigator@demo.claimshield", "wrong-password").status_code == 401
    assert _login(client, "nobody@demo.claimshield", "whatever").status_code == 401
    assert _login(client, "auditor@demo.claimshield", "demo-auditor").status_code == 200
    events = client.get("/api/v1/audit", params={"action": "auth.login_failed"}).json()["events"]
    reasons = {e["payload"]["reason"] for e in events}
    assert {"bad_password", "unknown_user"} <= reasons
    assert all("wrong-password" not in str(e["payload"]) for e in events)
    assert client.get("/api/v1/audit/verify").json()["intact"] is True


def test_overlong_password_is_rejected(client: TestClient) -> None:
    assert _login(client, "investigator@demo.claimshield", "x" * 257).status_code == 422


def test_session_status_answers_anonymous_visitors_with_200(client: TestClient) -> None:
    anonymous = client.get("/api/v1/auth/session")
    assert anonymous.status_code == 200
    assert anonymous.json() == {"authenticated": False, "user": None, "refresh_available": False}
    assert client.get("/api/v1/auth/me").status_code == 401
    assert _login(client, "manager@demo.claimshield", "demo-manager").status_code == 200
    signed_in = client.get("/api/v1/auth/session").json()
    assert signed_in["authenticated"] is True
    assert signed_in["user"]["role"] == "manager"
    client.cookies.set("cs_access", "not-a-jwt")
    stale = client.get("/api/v1/auth/session").json()
    assert stale["authenticated"] is False
    assert stale["refresh_available"] is True
