from __future__ import annotations

from typing import Any

from fastapi import APIRouter, Depends
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from claimshield.api.deps import get_db, require_internal_token
from claimshield.auth.service import seed_system_user
from claimshield.core.config import Settings, get_settings
from claimshield.db.models import User
from claimshield.ingest.s3_ingest import ingest_s3_object
from claimshield.ingest.store import build_store

router = APIRouter(prefix="/api/v1/aws", tags=["aws"])


class IngestBody(BaseModel):
    bucket: str = Field(min_length=3, max_length=128)
    key: str = Field(min_length=1, max_length=512)
    etag: str | None = Field(default=None, max_length=128)
    event_id: str | None = Field(default=None, max_length=128)


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
