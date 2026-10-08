from __future__ import annotations

from fastapi import APIRouter, Depends
from pydantic import BaseModel, Field
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from claimshield.api.deps import check_csrf, get_db, require
from claimshield.core.config import Settings, get_settings
from claimshield.core.errors import NotFound
from claimshield.db.models import Alert, Batch, Case, CaseRisk, PipelineRun, QueueOverride, User
from claimshield.pipeline.service import (
    latest_batch,
    latest_run,
    load_synthetic_batch,
    recompute_run,
)
from claimshield.queue.explain import run_payload, screening_days_left, why_rank
from claimshield.queue.rank import rank_pack_for_case, recommendation_for
from claimshield.risk.present import risk_fields

router = APIRouter(prefix="/api/v1", tags=["batches"])


class LoadBatchBody(BaseModel):
    adapter: str = Field(default="synthetic", max_length=32)
    profile: str = Field(default="tiny", max_length=32)
    seed: int = 7
    horizon_days: int = Field(default=60, ge=1, le=365)
    capacity_hours: float = Field(default=40.0, gt=0, le=10_000)
    max_slots: int = Field(default=20, ge=1, le=200)
    member_weight: float = Field(default=1.0, ge=0.25, le=3.0)
    run_now: bool = True


class BatchOut(BaseModel):
    batch_id: str
    adapter: str
    status: str
    profile: str | None
    seed: int | None
    load_report: dict
    run: dict | None = None


class RecomputeBody(BaseModel):
    batch_id: str | None = Field(default=None, max_length=32)
    horizon_days: int = Field(default=60, ge=1, le=365)
    capacity_hours: float = Field(default=40.0, gt=0, le=10_000)
    max_slots: int = Field(default=20, ge=1, le=200)
    member_weight: float = Field(default=1.0, ge=0.25, le=3.0)
    harm_lambda: float | None = Field(default=None, gt=0)


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
        max_slots=body.max_slots,
        member_weight=body.member_weight,
        run_now=body.run_now,
    )
    return BatchOut(
        batch_id=batch.batch_id,
        adapter=batch.adapter,
        status=batch.status,
        profile=batch.profile,
        seed=batch.seed,
        load_report=batch.load_report,
        run=(
            run.summary
            | {
                "run_id": run.run_id,
                "status": run.status,
                "batch_id": run.batch_id,
            }
            if run
            else None
        ),
    )


@router.post("/runs", dependencies=[Depends(check_csrf)])
def start_run(
    body: RecomputeBody,
    session: Session = Depends(get_db),
    settings: Settings = Depends(get_settings),
    user: User = Depends(require("run:start")),
) -> dict:
    batch = session.get(Batch, body.batch_id) if body.batch_id else latest_batch(session)
    if body.batch_id and batch is None:
        raise NotFound("batch not found")
    run = recompute_run(
        session,
        user=user,
        settings=settings,
        batch=batch,
        horizon_days=body.horizon_days,
        capacity_hours=body.capacity_hours,
        max_slots=body.max_slots,
        member_weight=body.member_weight,
        harm_lambda=body.harm_lambda,
    )
    n_alerts = session.execute(select(Alert).where(Alert.run_id == run.run_id)).scalars().all()
    n_cases = session.execute(select(Case).where(Case.run_id == run.run_id)).scalars().all()
    return run_payload(run, n_alerts=len(n_alerts), n_cases=len(n_cases))


@router.get("/runs/current")
def get_current_run(
    session: Session = Depends(get_db),
    _: User = Depends(require("queue:read")),
) -> dict:
    run = latest_run(session)
    if run is None:
        raise NotFound("no completed run")
    n_alerts = session.execute(select(Alert).where(Alert.run_id == run.run_id)).scalars().all()
    n_cases = session.execute(select(Case).where(Case.run_id == run.run_id)).scalars().all()
    return run_payload(run, n_alerts=len(n_alerts), n_cases=len(n_cases))


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
    runs = (
        session.execute(
            select(PipelineRun)
            .where(PipelineRun.batch_id == batch_id)
            .order_by(PipelineRun.created_at.desc())
        )
        .scalars()
        .all()
    )
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
    return run_payload(run, n_alerts=len(n_alerts), n_cases=len(n_cases))


@router.get("/runs/{run_id}/queue")
def get_queue(
    run_id: str,
    session: Session = Depends(get_db),
    _: User = Depends(require("queue:read")),
) -> list[dict]:
    run = session.get(PipelineRun, run_id)
    if run is None:
        raise NotFound("run not found")
    cases = list(session.execute(select(Case).where(Case.run_id == run_id)).scalars().all())
    member_weight = float((run.summary or {}).get("member_weight") or 1.0)
    horizon = int(run.horizon_days or 60)
    packs = {
        case.case_id: rank_pack_for_case(
            case, horizon_days=horizon, peers=cases, member_weight=member_weight
        )
        for case in cases
    }
    today = [c for c in cases if c.lane in {"harm_priority", "selected"}]
    today.sort(key=lambda c: packs[c.case_id]["composite"], reverse=True)
    ranks = {c.case_id: i + 1 for i, c in enumerate(today)}
    latest_override: dict[str, QueueOverride] = {}
    for row in session.execute(
        select(QueueOverride)
        .where(QueueOverride.run_id == run_id)
        .order_by(QueueOverride.created_at.desc())
    ).scalars():
        latest_override.setdefault(row.case_id, row)
    order = {"harm_priority": 0, "selected": 1, "needs_evidence": 2, "overflow": 3}
    cases = sorted(
        cases,
        key=lambda c: (order.get(c.lane, 9), -packs[c.case_id]["composite"]),
    )
    alert_counts = dict(
        session.execute(
            select(Alert.case_id, func.count()).where(Alert.run_id == run_id).group_by(Alert.case_id)
        ).all()
    )
    risks = {
        r.case_id: r
        for r in session.execute(select(CaseRisk).where(CaseRisk.run_id == run_id)).scalars()
    }
    return [
        _case_brief(
            c,
            factors=packs[c.case_id],
            queue_rank=ranks.get(c.case_id),
            override=latest_override.get(c.case_id),
            n_alerts=int(alert_counts.get(c.case_id) or 0),
            risk=risks.get(c.case_id),
        )
        for c in cases
    ]


def _case_brief(
    case: Case,
    *,
    factors: dict | None = None,
    queue_rank: int | None = None,
    override: QueueOverride | None = None,
    n_alerts: int = 0,
    risk: CaseRisk | None = None,
) -> dict:
    pack = factors or {}
    shown = override if override and override.action != "release" else None
    entity_ids = case.entity_ids or [case.primary_entity_id]
    n_entities = len(entity_ids)
    return {
        "case_id": case.case_id,
        "lane": case.lane,
        "status": case.status,
        "primary_entity_id": case.primary_entity_id,
        "entity_ids": entity_ids,
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
        **risk_fields(case, risk),
        "sla_due": case.sla_due.isoformat() if case.sla_due else None,
        "screening_days_left": screening_days_left(case),
        "rank_factors": pack,
        "queue_rank": queue_rank,
        "recommendation": recommendation_for(case.lane),
        "why_rank": why_rank(case, pack),
        "alert_group": {
            "n_entities": n_entities,
            "n_alerts": n_alerts,
            "urgent": case.harm >= 4,
            "text": (
                "Linked NPIs (owner, TIN, contact, or referral). Comparison peers are not in this case."
                if n_entities > 1
                else "Alerts for this provider are grouped on the portal; there is no per-alert notice."
            ),
        },
        "override": (
            {
                "action": shown.action,
                "reason": shown.reason,
                "actor_id": shown.actor_id,
                "prior_lane": shown.prior_lane,
            }
            if shown
            else None
        ),
        "suspicion_only": True,
    }
