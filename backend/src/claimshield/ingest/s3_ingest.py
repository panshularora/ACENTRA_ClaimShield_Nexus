"""S3 CSV → existing persist_dataset + execute_run. Lambda stays a thin trigger."""

from __future__ import annotations

import hashlib
import json
import logging
from datetime import UTC, datetime
from typing import Any

from sqlalchemy.orm import Session

from claimshield.core.config import Settings
from claimshield.core.errors import PipelineFailed, ValidationFailed
from claimshield.db.models import IngestReceipt, User
from claimshield.ingest.csv_extract import (
    REQUIRED_TABLES,
    dataset_from_tables,
    extract_prefix,
    parse_csv_bytes,
    table_name_from_key,
)
from claimshield.ingest.store import ObjectStore, StoredObject, assert_safe_key
from claimshield.pipeline.service import load_csv_batch

log = logging.getLogger("claimshield.ingest")


def ingest_s3_object(
    session: Session,
    *,
    user: User,
    settings: Settings,
    store: ObjectStore,
    bucket: str,
    key: str,
    etag: str | None,
    event_id: str | None,
) -> dict[str, Any]:
    assert_safe_key(key, incoming_prefix=settings.s3_incoming_prefix)
    if bucket != settings.s3_bucket:
        raise ValidationFailed("unexpected bucket")

    log.info("S3_OBJECT_RECEIVED bucket=%s key=%s", bucket, key)
    prefix = extract_prefix(key)
    siblings = store.list_csv(bucket, prefix)
    by_table: dict[str, tuple[str, str]] = {}
    for sibling_key, sibling_etag in siblings:
        table = table_name_from_key(sibling_key)
        if table:
            by_table[table] = (sibling_key, sibling_etag)

    missing = [name for name in REQUIRED_TABLES if name not in by_table]
    if missing:
        log.info(
            "INGESTION_WAITING key=%s missing=%s",
            key,
            ",".join(missing),
        )
        return {
            "status": "waiting_for_tables",
            "bucket": bucket,
            "key": key,
            "missing_tables": missing,
        }

    fingerprint = _fingerprint(bucket, prefix, by_table)
    existing = session.get(IngestReceipt, fingerprint)
    if existing is not None and existing.status == "completed":
        log.info(
            "INGESTION_REQUEST_COMPLETED batch_id=%s status=already_processed",
            existing.batch_id,
        )
        return {
            "status": "already_processed",
            "batch_id": existing.batch_id,
            "run_id": existing.run_id,
            "bucket": bucket,
            "key": key,
            **(existing.payload or {}),
        }

    if existing is not None and existing.status == "processing":
        return {
            "status": "already_processed",
            "batch_id": existing.batch_id,
            "run_id": existing.run_id,
            "bucket": bucket,
            "key": key,
        }

    if existing is not None:
        session.delete(existing)
        session.flush()

    now = datetime.now(UTC)
    receipt = IngestReceipt(
        idempotency_key=fingerprint,
        status="processing",
        batch_id=None,
        run_id=None,
        bucket=bucket,
        object_prefix=prefix,
        trigger_key=key,
        event_id=event_id,
        payload={"etag": etag},
        created_at=now,
        updated_at=now,
    )
    session.add(receipt)
    session.flush()

    try:
        tables = {}
        trigger: StoredObject | None = None
        for table, (table_key, _table_etag) in by_table.items():
            obj = store.get(bucket, table_key)
            if table_key == key:
                trigger = obj
            tables[table] = parse_csv_bytes(obj.body, table=table, max_bytes=settings.ingest_max_bytes)
        if trigger is None:
            trigger = store.get(bucket, key)
        dataset = dataset_from_tables(tables, source=f"s3://{bucket}/{prefix}")
        log.info("INGESTION_REQUEST_STARTED key=%s tables=%s", key, len(tables))
        batch, run = load_csv_batch(
            session,
            user=user,
            settings=settings,
            dataset=dataset,
            source={"bucket": bucket, "prefix": prefix, "key": key},
        )
        claims_processed = len(dataset.tables.get("claim", []))
        alerts_generated = int((run.summary or {}).get("n_alerts") or 0) if run else 0
        cases_generated = int((run.summary or {}).get("n_cases") or 0) if run else 0
        high_risk = 0
        if run:
            lanes = (run.summary or {}).get("lanes") or {}
            high_risk = int(lanes.get("harm_priority") or 0)
        payload = {
            "claims_processed": claims_processed,
            "alerts_generated": alerts_generated,
            "cases_generated": cases_generated,
            "high_risk_cases": high_risk,
            "tables": sorted(tables),
        }
        receipt.status = "completed"
        receipt.batch_id = batch.batch_id
        receipt.run_id = run.run_id if run else None
        receipt.payload = payload
        receipt.updated_at = datetime.now(UTC)
        session.flush()
        _write_artifacts(
            store,
            settings=settings,
            bucket=bucket,
            key=key,
            trigger=trigger,
            batch_id=batch.batch_id,
            run_id=run.run_id if run else None,
            payload=payload,
        )
        log.info(
            "PROCESSING_COMPLETED batch_id=%s run_id=%s claims_processed=%s alerts_generated=%s cases_generated=%s",
            batch.batch_id,
            run.run_id if run else None,
            claims_processed,
            alerts_generated,
            cases_generated,
        )
        return {
            "status": "accepted",
            "batch_id": batch.batch_id,
            "run_id": run.run_id if run else None,
            "run_status": run.status if run else None,
            "bucket": bucket,
            "key": key,
            **payload,
        }
    except ValidationFailed as exc:
        receipt.status = "rejected"
        receipt.payload = {"error_type": "validation"}
        receipt.updated_at = datetime.now(UTC)
        session.flush()
        log.info("PROCESSING_FAILED error_type=validation key=%s", key)
        raise ValidationFailed(exc.detail) from exc
    except Exception as exc:
        receipt.status = "failed"
        receipt.payload = {"error_type": "pipeline"}
        receipt.updated_at = datetime.now(UTC)
        session.flush()
        log.exception("PROCESSING_FAILED error_type=pipeline key=%s", key)
        raise PipelineFailed("pipeline failed") from exc


def _fingerprint(bucket: str, prefix: str, by_table: dict[str, tuple[str, str]]) -> str:
    parts = [bucket, prefix] + [f"{name}={by_table[name][1]}" for name in sorted(by_table)]
    digest = hashlib.sha256("\n".join(parts).encode("utf-8")).hexdigest()
    return digest


def _write_artifacts(
    store: ObjectStore,
    *,
    settings: Settings,
    bucket: str,
    key: str,
    trigger: StoredObject | None,
    batch_id: str,
    run_id: str | None,
    payload: dict[str, Any],
) -> None:
    filename = key.rsplit("/", 1)[-1]
    processed_key = f"{settings.s3_processed_prefix.rstrip('/')}/{batch_id}/{filename}"
    results_key = f"{settings.s3_results_prefix.rstrip('/')}/{batch_id}.json"
    if processed_key.startswith(settings.s3_incoming_prefix) or results_key.startswith(settings.s3_incoming_prefix):
        return
    body = json.dumps(
        {
            "status": "completed",
            "batch_id": batch_id,
            "run_id": run_id,
            "source_key": key,
            **payload,
            "suspicion_only": True,
        },
        separators=(",", ":"),
    ).encode("utf-8")
    try:
        if trigger is not None:
            store.put(bucket, processed_key, trigger.body, "text/csv")
        store.put(bucket, results_key, body, "application/json")
    except Exception:
        log.exception("ARTIFACT_WRITE_FAILED batch_id=%s", batch_id)
