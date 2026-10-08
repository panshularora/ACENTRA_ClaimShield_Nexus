from __future__ import annotations

from fastapi import APIRouter, Depends
from sqlalchemy import select
from sqlalchemy.orm import Session

from claimshield.api.deps import get_db, require
from claimshield.core.errors import NotFound
from claimshield.db.models import Alert, Case, User

router = APIRouter(prefix="/api/v1/cases", tags=["cases"])


@router.get("/{case_id}")
def get_case(
    case_id: str,
    session: Session = Depends(get_db),
    _: User = Depends(require("case:read")),
) -> dict:
    case = session.get(Case, case_id)
    if case is None:
        raise NotFound("case not found")
    alerts = session.execute(select(Alert).where(Alert.case_id == case_id)).scalars().all()
    return {
        "case_id": case.case_id,
        "run_id": case.run_id,
        "status": case.status,
        "lane": case.lane,
        "assignee_id": case.assignee_id,
        "primary_entity_id": case.primary_entity_id,
        "primary_entity_type": case.primary_entity_type,
        "harm": case.harm,
        "severity": case.severity,
        "members_affected": case.members_affected,
        "flagged_dollars": case.flagged_dollars,
        "evidence_strength": case.evidence_strength,
        "estimated_hours": case.estimated_hours,
        "p_confirm": case.p_confirm,
        "f30": case.f30,
        "f60": case.f60,
        "f90": case.f90,
        "alerts": [
            {
                "alert_id": a.alert_id,
                "detector": a.detector,
                "rule_id": a.rule_id,
                "entity_id": a.entity_id,
                "score": a.score,
                "evidence": a.evidence,
                "line_ids": a.line_ids,
            }
            for a in alerts
        ],
    }
