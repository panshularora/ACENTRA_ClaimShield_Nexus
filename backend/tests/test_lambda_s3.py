from __future__ import annotations

import importlib.util
import json
from pathlib import Path
from types import ModuleType
from urllib.error import URLError

import pytest

ROOT = Path(__file__).resolve().parents[2]
FIXTURE = ROOT / "tests" / "fixtures" / "s3_event.json"
HANDLER = ROOT / "infra" / "lambda" / "claimshield-s3-processor" / "handler.py"


def load_handler() -> ModuleType:
    spec = importlib.util.spec_from_file_location("claimshield_s3_processor", HANDLER)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


@pytest.fixture(scope="module")
def handler():
    return load_handler()


def test_valid_s3_event_calls_ingest(handler) -> None:
    event = json.loads(FIXTURE.read_text(encoding="utf-8"))
    calls: list[dict] = []

    def post(payload, **_kwargs):
        calls.append(payload)
        return 200, {
            "status": "accepted",
            "batch_id": "BAT-1",
            "run_id": "RUN-1",
            "claims_processed": 3,
        }

    result = handler.handle_event(
        event,
        api_url="https://api.example.invalid",
        token="secret",
        allowed_bucket="claimshield-nexus-data-2026",
        post=post,
    )
    assert result["ok"] is True
    assert result["results"][0]["status"] == "accepted"
    assert calls[0]["key"] == "incoming/claim.csv"
    assert calls[0]["bucket"] == "claimshield-nexus-data-2026"


def test_non_csv_object_is_ignored(handler) -> None:
    event = {
        "Records": [
            {
                "s3": {
                    "bucket": {"name": "claimshield-nexus-data-2026"},
                    "object": {"key": "incoming/notes.txt"},
                }
            }
        ]
    }
    result = handler.handle_event(
        event,
        api_url="https://api.example.invalid",
        token="secret",
        allowed_bucket="claimshield-nexus-data-2026",
        post=lambda *_a, **_k: pytest.fail("should not call api"),
    )
    assert result["results"][0]["status"] == "ignored"
    assert result["results"][0]["reason"] == "not_csv"


def test_wrong_prefix_is_ignored(handler) -> None:
    event = {
        "Records": [
            {
                "s3": {
                    "bucket": {"name": "claimshield-nexus-data-2026"},
                    "object": {"key": "processed/claim.csv"},
                }
            }
        ]
    }
    result = handler.handle_event(
        event,
        api_url="https://api.example.invalid",
        token="secret",
        allowed_bucket="claimshield-nexus-data-2026",
        post=lambda *_a, **_k: pytest.fail("should not call api"),
    )
    assert result["results"][0]["reason"] == "wrong_prefix"


def test_auth_failure_is_not_retried(handler) -> None:
    event = json.loads(FIXTURE.read_text(encoding="utf-8"))

    def post(*_a, **_k):
        return 401, {"detail": "internal token required"}

    result = handler.handle_event(
        event,
        api_url="https://api.example.invalid",
        token="secret",
        allowed_bucket="claimshield-nexus-data-2026",
        post=post,
    )
    assert result["results"][0]["reason"] == "authentication"


def test_processing_failure_raises(handler) -> None:
    event = json.loads(FIXTURE.read_text(encoding="utf-8"))

    def post(*_a, **_k):
        return 500, {"title": "Internal error"}

    with pytest.raises(RuntimeError, match="backend_error"):
        handler.handle_event(
            event,
            api_url="https://api.example.invalid",
            token="secret",
            allowed_bucket="claimshield-nexus-data-2026",
            post=post,
        )


def test_backend_unavailable_raises(handler) -> None:
    event = json.loads(FIXTURE.read_text(encoding="utf-8"))

    def post(*_a, **_k):
        raise ConnectionError("backend_unavailable")

    with pytest.raises(ConnectionError):
        handler.handle_event(
            event,
            api_url="https://api.example.invalid",
            token="secret",
            allowed_bucket="claimshield-nexus-data-2026",
            post=post,
        )


def test_env_reads_s3_input_prefix(handler, monkeypatch) -> None:
    monkeypatch.delenv("CLAIMSHIELD_S3_INCOMING_PREFIX", raising=False)
    monkeypatch.setenv("S3_INPUT_PREFIX", "incoming/")
    monkeypatch.delenv("CLAIMSHIELD_S3_BUCKET", raising=False)
    monkeypatch.setenv("S3_BUCKET", "claimshield-nexus-data-2026")
    assert handler._env("CLAIMSHIELD_S3_INCOMING_PREFIX", "S3_INPUT_PREFIX", default="x/") == "incoming/"
    assert handler._env("CLAIMSHIELD_S3_BUCKET", "S3_BUCKET", default="other") == "claimshield-nexus-data-2026"


def test_post_ingest_maps_url_error(handler, monkeypatch) -> None:
    def boom(_request, timeout=0):
        raise URLError("down")

    monkeypatch.setattr(handler.urllib.request, "urlopen", boom)
    with pytest.raises(ConnectionError, match="backend_unavailable"):
        handler.post_ingest(
            {"bucket": "b", "key": "incoming/claim.csv"},
            api_url="https://api.example.invalid",
            token="secret",
        )
