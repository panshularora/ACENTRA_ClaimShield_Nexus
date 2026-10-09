"""S3/Lambda ingest: ObjectCreated → POST /ingest → persist_dataset + execute_run."""

from __future__ import annotations

from typing import Any

from fastapi import APIRouter, Depends
from pydantic import BaseModel, Field
from sqlalchemy import select
from sqlalchemy.orm import Session

from claimshield.api.deps import get_db, require, require_internal_token
from claimshield.auth.service import seed_system_user
from claimshield.core.config import Settings, get_settings
from claimshield.db.models import IngestReceipt, User
from claimshield.ingest.s3_ingest import ingest_s3_object
from claimshield.ingest.store import build_store

router = APIRouter(prefix="/api/v1/aws", tags=["aws"])


class IngestBody(BaseModel):
    bucket: str = Field(min_length=3, max_length=128)
    key: str = Field(min_length=1, max_length=512)
    etag: str | None = Field(default=None, max_length=128)
    event_id: str | None = Field(default=None, max_length=128)


@router.get("/status")
def aws_status(
    session: Session = Depends(get_db),
    settings: Settings = Depends(get_settings),
    _: User = Depends(require("queue:read")),
) -> dict[str, Any]:
    """Public AWS wiring for the manager desk. Token and keys are never returned."""
    receipts = session.execute(select(IngestReceipt).order_by(IngestReceipt.updated_at.desc()).limit(5)).scalars().all()
    body = settings.aws_public_status()
    body["recent_ingests"] = [
        {
            "status": row.status,
            "batch_id": row.batch_id,
            "run_id": row.run_id,
            "bucket": row.bucket,
            "trigger_key": row.trigger_key,
            "updated_at": row.updated_at.isoformat() if row.updated_at else None,
        }
        for row in receipts
    ]
    return body


@router.post("/ingest", dependencies=[Depends(require_internal_token)])
def ingest_from_s3(
    body: IngestBody,
    session: Session = Depends(get_db),
    settings: Settings = Depends(get_settings),
) -> dict[str, Any]:
    user: User = seed_system_user(session)
    store = build_store(settings)
    return ingest_s3_object(
        session,
        user=user,
        settings=settings,
        store=store,
        bucket=body.bucket,
        key=body.key,
        etag=body.etag,
        event_id=body.event_id,
    )
