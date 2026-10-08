from __future__ import annotations

import httpx
import pytest
from fastapi.testclient import TestClient

from claimshield.api.deps import reset_engine
from claimshield.auth.service import login_limiter
from claimshield.core.config import get_settings


@pytest.fixture(autouse=True)
def _reset_limiter() -> None:
    login_limiter.reset()
    yield
    login_limiter.reset()


def _csrf_hook(test_client: TestClient):
    """Echo the CSRF cookie in X-CSRF-Token on writes, as the web client does."""

    def hook(request: httpx.Request) -> None:
        if request.method in {"GET", "HEAD"} or "x-csrf-token" in request.headers:
            return
        token = next((c.value for c in test_client.cookies.jar if c.name == "cs_csrf"), None)
        if token:
            request.headers["X-CSRF-Token"] = token

    return hook


@pytest.fixture
def client(tmp_path, monkeypatch) -> TestClient:
    db = tmp_path / "claimshield.db"
    monkeypatch.setenv("CLAIMSHIELD_DATABASE_URL", f"sqlite+pysqlite:///{db.as_posix()}")
    monkeypatch.setenv("CLAIMSHIELD_JWT_SIGNING_KEY", "test-signing-key-at-least-32-bytes-long")
    monkeypatch.setenv("CLAIMSHIELD_COOKIE_SECURE", "false")
    monkeypatch.setenv("CLAIMSHIELD_DEMO_MODE", "true")
    get_settings.cache_clear()
    reset_engine()
    from claimshield.api.main import create_app

    app = create_app()
    with TestClient(app) as test_client:
        test_client.event_hooks["request"].append(_csrf_hook(test_client))
        yield test_client
    reset_engine()
    get_settings.cache_clear()


@pytest.fixture(scope="session")
def tiny_dataset():
    from claimshield.synth.generator import generate

    return generate("tiny", 7)
