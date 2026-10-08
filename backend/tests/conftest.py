from __future__ import annotations

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


@pytest.fixture
def client(tmp_path, monkeypatch) -> TestClient:
    db = tmp_path / "claimshield.db"
    monkeypatch.setenv("CLAIMSHIELD_DATABASE_URL", f"sqlite+pysqlite:///{db.as_posix()}")
    monkeypatch.setenv("CLAIMSHIELD_JWT_SIGNING_KEY", "test-signing-key-32-bytes-min!!")
    monkeypatch.setenv("CLAIMSHIELD_COOKIE_SECURE", "false")
    monkeypatch.setenv("CLAIMSHIELD_DEMO_MODE", "true")
    get_settings.cache_clear()
    reset_engine()
    from claimshield.api.main import create_app

    app = create_app()
    with TestClient(app) as test_client:
        yield test_client
    reset_engine()
    get_settings.cache_clear()


@pytest.fixture(scope="session")
def tiny_dataset():
    from claimshield.synth.generator import generate

    return generate("tiny", 7)
