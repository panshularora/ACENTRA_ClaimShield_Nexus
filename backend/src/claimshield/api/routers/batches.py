from __future__ import annotations

from fastapi import APIRouter, Depends
from pydantic import BaseModel, Field
from sqlalchemy import select
from sqlalchemy.orm import Session

from claimshield.api.deps import check_csrf, get_db, require
from claimshield.core.config import Settings, get_settings
from claimshield.core.errors import NotFound
from claimshield.db.models import Alert, Batch, Case, PipelineRun, User
from claimshield.pipeline.service import load_synthetic_batch

router = APIRouter(prefix="/api/v1", tags=["batches"])


class LoadBatchBody(BaseModel):
    adapter: str = "synthetic"
    profile: str = "tiny"
    seed: int = 7
    horizon_days: int = 60
    capacity_hours: float = Field(default=40.0, gt=0)
    run_now: bool = True


class BatchOut(BaseModel):
    batch_id: str
    adapter: str
    status: str
    profile: str | None
    seed: int | None
    load_report: dict
    run: dict | None = None


@router.post("/batches", dependencies=[Depends(check_csrf)])
def create_batch(
    body: LoadBatchBody,
    session: Session = Depends(get_db),
    settings: Settings = Depends(get_settings),
    user: User = Depends(require("batch:load")),
) -> BatchOut:
    batch, run = load_synthetic_batch(
        session,
        user=user,
        settings=settings,
        profile=body.profile,
        seed=body.seed,
        horizon_days=body.horizon_days,
        capacity_hours=body.capacity_hours,
        run_now=body.run_now,
    )
    return BatchOut(
        batch_id=batch.batch_id,
        adapter=batch.adapter,
        status=batch.status,
        profile=batch.profile,
        seed=batch.seed,
        load_report=batch.load_report,
        run=run.summary | {"run_id": run.run_id, "status": run.status} if run else None,
    )


@router.get("/batches")
def list_batches(
    session: Session = Depends(get_db),
    _: User = Depends(require("batch:read")),
) -> list[dict]:
    rows = session.execute(select(Batch).order_by(Batch.created_at.desc())).scalars().all()
    return [
        {
            "batch_id": b.batch_id,
            "adapter": b.adapter,
            "status": b.status,
            "profile": b.profile,
            "seed": b.seed,
            "created_at": b.created_at.isoformat() if b.created_at else None,
        }
        for b in rows
    ]


@router.get("/batches/{batch_id}")
def get_batch(
    batch_id: str,
    session: Session = Depends(get_db),
    _: User = Depends(require("batch:read")),
) -> dict:
    batch = session.get(Batch, batch_id)
    if batch is None:
        raise NotFound("batch not found")
    runs = session.execute(select(PipelineRun).where(PipelineRun.batch_id == batch_id)).scalars().all()
    return {
        "batch_id": batch.batch_id,
        "adapter": batch.adapter,
        "status": batch.status,
        "profile": batch.profile,
        "seed": batch.seed,
        "load_report": batch.load_report,
        "runs": [{"run_id": r.run_id, "status": r.status, "summary": r.summary} for r in runs],
    }


@router.get("/runs/{run_id}")
def get_run(
    run_id: str,
    session: Session = Depends(get_db),
    _: User = Depends(require("queue:read")),
) -> dict:
    run = session.get(PipelineRun, run_id)
    if run is None:
        raise NotFound("run not found")
    n_alerts = session.execute(select(Alert).where(Alert.run_id == run_id)).scalars().all()
    n_cases = session.execute(select(Case).where(Case.run_id == run_id)).scalars().all()
    return {
        "run_id": run.run_id,
        "batch_id": run.batch_id,
        "status": run.status,
        "summary": run.summary,
        "n_alerts": len(n_alerts),
        "n_cases": len(n_cases),
    }


@router.get("/runs/{run_id}/queue")
def get_queue(
    run_id: str,
    session: Session = Depends(get_db),
    _: User = Depends(require("queue:read")),
) -> list[dict]:
    run = session.get(PipelineRun, run_id)
    if run is None:
        raise NotFound("run not found")
    cases = session.execute(select(Case).where(Case.run_id == run_id)).scalars().all()
    order = {"harm_priority": 0, "selected": 1, "needs_evidence": 2, "overflow": 3}
    cases = sorted(
        cases,
        key=lambda c: (order.get(c.lane, 9), -(c.expected_value or 0.0)),
    )
    return [_case_brief(c) for c in cases]


def _case_brief(case: Case) -> dict:
    return {
        "case_id": case.case_id,
        "lane": case.lane,
        "status": case.status,
        "primary_entity_id": case.primary_entity_id,
        "entity_ids": case.entity_ids or [case.primary_entity_id],
        "harm": case.harm,
        "severity": case.severity,
        "members_affected": case.members_affected,
        "flagged_dollars": case.flagged_dollars,
        "evidence_strength": case.evidence_strength,
        "estimated_hours": case.estimated_hours,
        "p_confirm": case.p_confirm,
        "expected_value": case.expected_value,
        "f30": case.f30,
        "f60": case.f60,
        "f90": case.f90,
    }
