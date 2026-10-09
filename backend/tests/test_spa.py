from fastapi.testclient import TestClient


def test_spa_fallback_serves_index(tmp_path, monkeypatch) -> None:
    spa = tmp_path / "spa"
    spa.mkdir()
    (spa / "index.html").write_text("<!doctype html><title>ClaimShield</title>", encoding="utf-8")
    (spa / "favicon.svg").write_text("<svg xmlns='http://www.w3.org/2000/svg'></svg>", encoding="utf-8")
    db = tmp_path / "claimshield.db"
    monkeypatch.setenv("CLAIMSHIELD_DATABASE_URL", f"sqlite+pysqlite:///{db.as_posix()}")
    monkeypatch.setenv("CLAIMSHIELD_JWT_SIGNING_KEY", "test-signing-key-at-least-32-bytes-long")
    monkeypatch.setenv("CLAIMSHIELD_COOKIE_SECURE", "false")
    monkeypatch.setenv("CLAIMSHIELD_DEMO_MODE", "true")
    monkeypatch.setenv("CLAIMSHIELD_SPA_DIR", spa.as_posix())
    from claimshield.api.deps import reset_engine
    from claimshield.core.config import get_settings

    get_settings.cache_clear()
    reset_engine()
    from claimshield.api.main import create_app

    app = create_app()
    with TestClient(app) as client:
        page = client.get("/login")
        assert page.status_code == 200
        assert "ClaimShield" in page.text
        asset = client.get("/favicon.svg")
        assert asset.status_code == 200
        missing_api = client.get("/api/v1/does-not-exist")
        assert missing_api.status_code == 404
        health = client.get("/healthz")
        assert health.status_code == 200
    reset_engine()
    get_settings.cache_clear()
