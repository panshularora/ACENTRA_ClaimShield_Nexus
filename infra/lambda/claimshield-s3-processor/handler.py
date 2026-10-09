"""Thin S3 → ClaimShield API trigger. No fraud rules live here."""

from __future__ import annotations

import json
import os
import time
import urllib.error
import urllib.request
from typing import Any
from urllib.parse import unquote_plus

DEFAULT_BUCKET = "claimshield-nexus-data-2026"
INCOMING_PREFIX = "incoming/"
REQUEST_TIMEOUT_S = 120


def log(level: str, event: str, **fields: Any) -> None:
    parts = " ".join(f"{key}={_safe(value)}" for key, value in fields.items() if value is not None)
    print(f"[{level}] {event} {parts}".strip())


def _safe(value: Any) -> str:
    text = str(value)
    lowered = text.lower()
    if "token" in lowered or "password" in lowered or "authorization" in lowered:
        return "[redacted]"
    return text.replace("\n", " ")[:240]


def extract_objects(event: dict[str, Any]) -> list[dict[str, str]]:
    records = event.get("Records") or []
    objects: list[dict[str, str]] = []
    for record in records:
        s3 = record.get("s3") or {}
        bucket = ((s3.get("bucket") or {}).get("name")) or ""
        key = unquote_plus(str((s3.get("object") or {}).get("key") or ""))
        etag = str((s3.get("object") or {}).get("eTag") or "").strip('"')
        event_id = str(record.get("responseElements", {}).get("x-amz-request-id") or record.get("eventName") or "")
        objects.append(
            {
                "bucket": bucket,
                "key": key,
                "etag": etag,
                "event_id": event_id or str(record.get("eventTime") or ""),
                "event_name": str(record.get("eventName") or ""),
            }
        )
    return objects


def should_process(bucket: str, key: str, *, allowed_bucket: str, incoming_prefix: str) -> tuple[bool, str]:
    if not bucket or bucket != allowed_bucket:
        return False, "unexpected_bucket"
    if ".." in key.split("/"):
        return False, "invalid_key"
    prefix = incoming_prefix if incoming_prefix.endswith("/") else incoming_prefix + "/"
    if not key.startswith(prefix):
        return False, "wrong_prefix"
    if not key.lower().endswith(".csv"):
        return False, "not_csv"
    return True, "ok"


def post_ingest(
    payload: dict[str, Any],
    *,
    api_url: str,
    token: str,
    opener: Any | None = None,
) -> tuple[int, dict[str, Any]]:
    url = api_url.rstrip("/") + "/api/v1/aws/ingest"
    body = json.dumps(payload).encode("utf-8")
    request = urllib.request.Request(
        url,
        data=body,
        method="POST",
        headers={
            "Content-Type": "application/json",
            "X-ClaimShield-Internal-Token": token,
        },
    )
    handler = opener or urllib.request.urlopen
    try:
        with handler(request, timeout=REQUEST_TIMEOUT_S) as response:
            raw = response.read()
            status = getattr(response, "status", 200)
            parsed = json.loads(raw.decode("utf-8") or "{}")
            return int(status), parsed if isinstance(parsed, dict) else {"status": "accepted"}
    except urllib.error.HTTPError as exc:
        raw = exc.read() if exc.fp else b"{}"
        try:
            parsed = json.loads(raw.decode("utf-8") or "{}")
        except json.JSONDecodeError:
            parsed = {"title": "http_error"}
        if not isinstance(parsed, dict):
            parsed = {"title": "http_error"}
        return int(exc.code), parsed
    except urllib.error.URLError as exc:
        raise ConnectionError("backend_unavailable") from exc


def emit_metrics(result: dict[str, Any], *, environment: str) -> None:
    if result.get("status") not in {"accepted", "already_processed"}:
        if result.get("status") in {"rejected"} or result.get("error_type"):
            _emf("ProcessingFailures", 1, environment)
        return
    _emf("ClaimsProcessed", int(result.get("claims_processed") or 0), environment)
    _emf("AlertsGenerated", int(result.get("alerts_generated") or 0), environment)
    _emf("CasesGenerated", int(result.get("cases_generated") or 0), environment)
    _emf("HighRiskCases", int(result.get("high_risk_cases") or 0), environment)


def _emf(name: str, value: int, environment: str) -> None:
    if value <= 0 and name != "ProcessingFailures":
        return
    document = {
        "_aws": {
            "Timestamp": int(time.time() * 1000),
            "CloudWatchMetrics": [
                {
                    "Namespace": "ClaimShield",
                    "Dimensions": [["Environment", "Pipeline"]],
                    "Metrics": [{"Name": name, "Unit": "Count"}],
                }
            ],
        },
        "Environment": environment,
        "Pipeline": "s3-ingest",
        name: value,
    }
    print(json.dumps(document, separators=(",", ":")))


def handle_event(
    event: dict[str, Any],
    *,
    api_url: str,
    token: str,
    allowed_bucket: str,
    incoming_prefix: str = INCOMING_PREFIX,
    environment: str = "hackathon",
    post=post_ingest,
) -> dict[str, Any]:
    results: list[dict[str, Any]] = []
    for obj in extract_objects(event):
        bucket = obj["bucket"]
        key = obj["key"]
        log("INFO", "S3_OBJECT_RECEIVED", bucket=bucket, key=key)
        ok, reason = should_process(
            bucket, key, allowed_bucket=allowed_bucket, incoming_prefix=incoming_prefix
        )
        if not ok:
            log("INFO", "S3_OBJECT_IGNORED", bucket=bucket, key=key, reason=reason)
            results.append({"key": key, "status": "ignored", "reason": reason})
            continue
        if not token:
            log("ERROR", "AUTH_CONFIG_MISSING")
            results.append({"key": key, "status": "error", "reason": "auth_config_missing"})
            raise RuntimeError("CLAIMSHIELD_INTERNAL_TOKEN is not set")
        if not api_url:
            log("ERROR", "PROCESSING_FAILED", error_type="config", message="api_url_missing")
            raise RuntimeError("CLAIMSHIELD_API_URL is not set")
        log("INFO", "INGESTION_REQUEST_STARTED", key=key)
        try:
            status, body = post(
                {
                    "bucket": bucket,
                    "key": key,
                    "etag": obj.get("etag") or None,
                    "event_id": obj.get("event_id") or None,
                },
                api_url=api_url,
                token=token,
            )
        except ConnectionError:
            log("ERROR", "PROCESSING_FAILED", error_type="backend_unavailable", key=key)
            raise
        ingest_status = str(body.get("status") or body.get("title") or "error")
        if status == 401 or status == 403:
            log("ERROR", "PROCESSING_FAILED", error_type="authentication", http_status=status)
            results.append({"key": key, "status": "error", "reason": "authentication"})
            continue
        if status >= 500:
            log("ERROR", "PROCESSING_FAILED", error_type="backend", http_status=status)
            raise RuntimeError("backend_error")
        if status == 422:
            log("ERROR", "PROCESSING_FAILED", error_type="validation", http_status=status)
            emit_metrics({"status": "rejected", "error_type": "validation"}, environment=environment)
            results.append({"key": key, "status": "rejected", "reason": "validation"})
            continue
        log(
            "INFO",
            "INGESTION_REQUEST_COMPLETED",
            batch_id=body.get("batch_id"),
            status=ingest_status,
        )
        if ingest_status == "accepted":
            log(
                "INFO",
                "PROCESSING_COMPLETED",
                batch_id=body.get("batch_id"),
                run_id=body.get("run_id"),
                claims_processed=body.get("claims_processed"),
                alerts_generated=body.get("alerts_generated"),
                cases_generated=body.get("cases_generated"),
            )
        emit_metrics(body, environment=environment)
        results.append({"key": key, "status": ingest_status, "http_status": status, **_public(body)})
    return {"ok": True, "results": results}


def _public(body: dict[str, Any]) -> dict[str, Any]:
    keep = (
        "batch_id",
        "run_id",
        "claims_processed",
        "alerts_generated",
        "cases_generated",
        "high_risk_cases",
        "missing_tables",
    )
    return {key: body[key] for key in keep if key in body}


def _env(*names: str, default: str = "") -> str:
    for name in names:
        value = os.environ.get(name)
        if value:
            return value
    return default


def lambda_handler(event: dict[str, Any], _context: Any) -> dict[str, Any]:
    # CLAIMSHIELD_INTERNAL_TOKEN must match FastAPI. S3_INPUT_PREFIX is the run-sheet name for incoming/.
    return handle_event(
        event,
        api_url=_env("CLAIMSHIELD_API_URL"),
        token=_env("CLAIMSHIELD_INTERNAL_TOKEN"),
        allowed_bucket=_env("CLAIMSHIELD_S3_BUCKET", "S3_BUCKET", default=DEFAULT_BUCKET),
        incoming_prefix=_env("CLAIMSHIELD_S3_INCOMING_PREFIX", "S3_INPUT_PREFIX", default=INCOMING_PREFIX),
        environment=_env("CLAIMSHIELD_ENVIRONMENT", default="hackathon"),
    )
