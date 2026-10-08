"""API view of a case's risk scores. Shared by the queue and the case workspace."""

from __future__ import annotations

from typing import Any

from sqlalchemy.orm import Session

from claimshield.db.models import Case, CaseRisk
from claimshield.risk.heuristic import HEURISTIC_VERSION


def risk_fields(case: Case, risk: CaseRisk | None) -> dict[str, Any]:
    """New risk fields. ``p_confirm`` and ``f30/f60/f90`` stay where they were for old clients."""
    detail = dict(risk.detail or {}) if risk is not None else {}
    return {
        "risk_30": case.f30,
        "risk_60": case.f60,
        "risk_90": case.f90,
        "score_kind": risk.score_kind if risk is not None else "uncalibrated_heuristic",
        "model_version": risk.model_version if risk is not None else HEURISTIC_VERSION,
        "calibrated": bool(risk.calibrated) if risk is not None else False,
        "risk_as_of": detail.get("as_of"),
        "risk_subject": detail.get("risk_subject"),
        "monthly_hazards": detail.get("monthly_hazards"),
        "risk_factors": detail.get("risk_factors") or [],
        "p_confirm_factors": detail.get("p_confirm_factors") or [],
    }


def case_risk(session: Session, case_id: str) -> CaseRisk | None:
    return session.get(CaseRisk, case_id)


def score_label(risk: CaseRisk | None) -> str:
    if risk is not None and risk.score_kind == "trained_model":
        state = "calibrated" if risk.calibrated else "uncalibrated"
        return f"{state} model {risk.model_version}, trained on synthetic data"
    return "uncalibrated heuristic, not a probability"
