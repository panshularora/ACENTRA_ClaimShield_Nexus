from __future__ import annotations

import shutil
from collections.abc import Generator
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from claimshield.api.deps import reset_engine
from claimshield.core.config import get_settings

EXTRACT = Path(__file__).resolve().parents[2] / "data" / "generated" / "tiny"
TOKEN = "test-internal-token-do-not-commit"


@pytest.fixture
def aws_client(tmp_path, monkeypatch) -> Generator[TestClient, None, None]:
    db = tmp_path / "claimshield.db"
    monkeypatch.setenv("CLAIMSHIELD_DATABASE_URL", f"sqlite+pysqlite:///{db.as_posix()}")
    monkeypatch.setenv("CLAIMSHIELD_JWT_SIGNING_KEY", "test-signing-key-at-least-32-bytes-long")
    monkeypatch.setenv("CLAIMSHIELD_COOKIE_SECURE", "false")
    monkeypatch.setenv("CLAIMSHIELD_DEMO_MODE", "true")
    monkeypatch.setenv("CLAIMSHIELD_INTERNAL_TOKEN", TOKEN)
    monkeypatch.setenv("CLAIMSHIELD_S3_LOCAL_DIR", str(tmp_path))
    monkeypatch.setenv("CLAIMSHIELD_S3_BUCKET", "claimshield-nexus-data-2026")
    get_settings.cache_clear()
    reset_engine()
    from claimshield.api.main import create_app

    with TestClient(create_app()) as test_client:
        yield test_client
    reset_engine()
    get_settings.cache_clear()


def _copy_extract(incoming: Path) -> None:
    incoming.mkdir(parents=True, exist_ok=True)
    for path in EXTRACT.glob("*.csv"):
        if path.stem == "ground_truth":
            continue
        shutil.copy(path, incoming / path.name)


def test_missing_internal_token_is_401(aws_client: TestClient) -> None:
    res = aws_client.post(
        "/api/v1/aws/ingest",
        json={"bucket": "claimshield-nexus-data-2026", "key": "incoming/claim.csv"},
    )
    assert res.status_code == 401
    assert res.json()["detail"] == "internal token required"


def test_invalid_internal_token_is_401(aws_client: TestClient) -> None:
    res = aws_client.post(
        "/api/v1/aws/ingest",
        json={"bucket": "claimshield-nexus-data-2026", "key": "incoming/claim.csv"},
        headers={"X-ClaimShield-Internal-Token": "wrong-token"},
    )
    assert res.status_code == 401
    assert res.json()["detail"] == "internal token required"


def test_missing_token_when_unset(client: TestClient) -> None:
    res = client.post(
        "/api/v1/aws/ingest",
        json={"bucket": "claimshield-nexus-data-2026", "key": "incoming/claim.csv"},
        headers={"X-ClaimShield-Internal-Token": "anything"},
    )
    assert res.status_code == 401


def test_wrong_prefix_rejected(aws_client: TestClient) -> None:
    res = aws_client.post(
        "/api/v1/aws/ingest",
        json={"bucket": "claimshield-nexus-data-2026", "key": "processed/claim.csv"},
        headers={"X-ClaimShield-Internal-Token": TOKEN},
    )
    assert res.status_code == 422


def test_waiting_for_incomplete_extract(aws_client: TestClient, tmp_path) -> None:
    incoming = tmp_path / "incoming"
    incoming.mkdir()
    (incoming / "claim.csv").write_text("claim_id,member_id\nCLM-1,MBR-1\n", encoding="utf-8")
    res = aws_client.post(
        "/api/v1/aws/ingest",
        json={"bucket": "claimshield-nexus-data-2026", "key": "incoming/claim.csv", "etag": "1"},
        headers={"X-ClaimShield-Internal-Token": TOKEN},
    )
    assert res.status_code == 200
    body = res.json()
    assert body["status"] == "waiting_for_tables"
    assert "member" in body["missing_tables"]


def test_invalid_csv_rejected(aws_client: TestClient, tmp_path) -> None:
    incoming = tmp_path / "incoming"
    incoming.mkdir()
    files = {
        "member.csv": "member_id,name,dob,sex,location_id\nMBR-1,A,2020-01-01,F,LOC-1\n",
        "provider.csv": ("provider_id,name,kind,specialty,service_line,location_id\nPRV-1,P,md,pcp,pcp,LOC-1\n"),
        "claim.csv": "not,a,claim\n1,2,3\n",
        "claim_line.csv": (
            "line_id,claim_id,rendering_provider_id,dos_from,dos_to,code,charge,allowed,paid\n"
            "LN-1,CLM-1,PRV-1,2024-01-01,2024-01-01,EM-1,10,10,10\n"
        ),
    }
    for name, header in files.items():
        (incoming / name).write_text(header, encoding="utf-8")
    res = aws_client.post(
        "/api/v1/aws/ingest",
        json={"bucket": "claimshield-nexus-data-2026", "key": "incoming/claim.csv"},
        headers={"X-ClaimShield-Internal-Token": TOKEN},
    )
    assert res.status_code == 422


def test_successful_ingest_and_duplicate(aws_client: TestClient, tmp_path) -> None:
    _copy_extract(tmp_path / "incoming")
    headers = {"X-ClaimShield-Internal-Token": TOKEN}
    body = {
        "bucket": "claimshield-nexus-data-2026",
        "key": "incoming/claim.csv",
        "etag": "abc",
        "event_id": "evt-1",
    }
    first = aws_client.post("/api/v1/aws/ingest", json=body, headers=headers)
    assert first.status_code == 200, first.text
    payload = first.json()
    assert payload["status"] == "accepted"
    assert payload["batch_id"]
    assert payload["run_id"]
    assert payload["claims_processed"] >= 1
    assert payload["alerts_generated"] >= 1
    assert payload["cases_generated"] >= 1
    assert (tmp_path / "results" / f"{payload['batch_id']}.json").is_file()

    second = aws_client.post("/api/v1/aws/ingest", json=body, headers=headers)
    assert second.status_code == 200
    assert second.json()["status"] == "already_processed"
    assert second.json()["batch_id"] == payload["batch_id"]


def test_processing_failure(aws_client: TestClient, tmp_path, monkeypatch) -> None:
    _copy_extract(tmp_path / "incoming")

    def boom(*_a, **_k):
        raise RuntimeError("pipeline exploded")

    monkeypatch.setattr("claimshield.ingest.s3_ingest.load_csv_batch", boom)
    res = aws_client.post(
        "/api/v1/aws/ingest",
        json={"bucket": "claimshield-nexus-data-2026", "key": "incoming/claim.csv"},
        headers={"X-ClaimShield-Internal-Token": TOKEN},
    )
    assert res.status_code == 500


def test_local_batches_still_work_without_aws(client: TestClient) -> None:
    login = client.post(
        "/api/v1/auth/login",
        json={"email": "manager@demo.claimshield", "password": "demo-manager"},
    )
    assert login.status_code == 200
    res = client.post("/api/v1/batches", json={"profile": "tiny", "seed": 7, "run_now": False})
    assert res.status_code == 200
    assert res.json()["adapter"] == "synthetic"
