"""Browsable SIU history: decided cases, earlier-run cases, and prior investigations.

Outcome labels stay in {substantiated, education, referred, unsubstantiated}.
The product never labels fraud.
"""

from __future__ import annotations

from typing import Any

from sqlalchemy import select
from sqlalchemy.orm import Session

from claimshield.cases.common import iso
from claimshield.cases.decisions import CLOSED_STATUSES
from claimshield.db.models import Case, Decision, Investigation, InvestigationSubject, Provider
from claimshield.pipeline.service import latest_run

OUTCOME_LABELS = {
    "substantiated": "Substantiated",
    "education": "Education",
    "referred": "Referred",
    "unsubstantiated": "Unsubstantiated",
}
CASE_STATUS_OUTCOME = {
    "escalated": "referred",
    "dismissed": "unsubstantiated",
    "monitor": "education",
}
DECIDED_STATUSES = frozenset(
    {"escalated", "dismissed", "monitor", "needs_evidence", "pending_approval"}
)
STATUS_LABELS = {
    "open": "Open (earlier run)",
    "needs_evidence": "Gather records",
    "pending_approval": "Pending manager approval",
    "monitor": "Education",
    "escalated": "Referred",
    "dismissed": "Unsubstantiated",
}


def _status_label(status: str, outcome: str | None) -> str:
    if outcome and outcome in OUTCOME_LABELS:
        return OUTCOME_LABELS[outcome]
    return STATUS_LABELS.get(status, status.replace("_", " "))


def list_history(session: Session, *, limit: int = 200) -> dict[str, Any]:
    """Closed or earlier-run SIU cases plus extract investigations, newest first."""
    run = latest_run(session)
    current_run_id = run.run_id if run else None
    providers = {p.provider_id: p for p in session.execute(select(Provider)).scalars().all()}
    cases = list(session.execute(select(Case)).scalars().all())
    decisions = list(session.execute(select(Decision).order_by(Decision.created_at.desc())).scalars().all())
    latest_decision: dict[str, Decision] = {}
    for row in decisions:
        latest_decision.setdefault(row.case_id, row)

    items: list[dict[str, Any]] = []
    for case in cases:
        decided = case.status in DECIDED_STATUSES
        earlier = bool(current_run_id) and case.run_id != current_run_id
        if not decided and not earlier:
            continue
        provider = providers.get(case.primary_entity_id)
        decision = latest_decision.get(case.case_id)
        outcome = CASE_STATUS_OUTCOME.get(case.status)
        closed_at = None
        if decision is not None:
            stamp = decision.approved_at if case.status in CLOSED_STATUSES else decision.created_at
            closed_at = iso(stamp)
        items.append(
            {
                "kind": "case",
                "id": case.case_id,
                "case_id": case.case_id,
                "investigation_id": None,
                "provider_id": case.primary_entity_id,
                "provider_name": provider.name if provider else case.primary_entity_id,
                "npi": provider.npi_syn if provider else None,
                "specialty": provider.specialty if provider else None,
                "status": case.status,
                "lane": case.lane,
                "outcome": outcome,
                "outcome_label": _status_label(case.status, outcome),
                "action": decision.action if decision else None,
                "reason": (decision.reason[:180] if decision and decision.reason else None),
                "opened_at": None,
                "closed_at": closed_at,
                "run_id": case.run_id,
                "current_run": case.run_id == current_run_id,
                "flagged_dollars": case.flagged_dollars,
                "amount_identified": None,
                "amount_recovered": None,
                "harm": case.harm,
                "scheme_tag": None,
                "lead_source": None,
                "n_subjects": 1,
                "source": "siu_case",
            }
        )

    subjects = list(session.execute(select(InvestigationSubject)).scalars().all())
    by_inv: dict[str, list[str]] = {}
    for subject in subjects:
        by_inv.setdefault(subject.investigation_id, []).append(subject.provider_id)
    current_by_provider = {
        case.primary_entity_id: case.case_id for case in cases if case.run_id == current_run_id
    }
    investigations = list(session.execute(select(Investigation)).scalars().all())
    for inv in investigations:
        pids = by_inv.get(inv.investigation_id, [])
        provider_id = pids[0] if pids else None
        provider = providers.get(provider_id) if provider_id else None
        raw = inv.outcome if inv.outcome in OUTCOME_LABELS else None
        items.append(
            {
                "kind": "investigation",
                "id": inv.investigation_id,
                "case_id": current_by_provider.get(provider_id) if provider_id else None,
                "investigation_id": inv.investigation_id,
                "provider_id": provider_id,
                "provider_name": provider.name if provider else (provider_id or inv.investigation_id),
                "npi": provider.npi_syn if provider else None,
                "specialty": provider.specialty if provider else None,
                "status": "closed" if inv.closed else "open",
                "lane": None,
                "outcome": raw,
                "outcome_label": _status_label("closed" if inv.closed else "open", raw),
                "action": None,
                "reason": inv.closed_reason,
                "opened_at": iso(inv.opened),
                "closed_at": iso(inv.closed),
                "run_id": None,
                "current_run": False,
                "flagged_dollars": None,
                "amount_identified": inv.amount_identified,
                "amount_recovered": inv.amount_recovered,
                "harm": None,
                "scheme_tag": inv.scheme_tag,
                "lead_source": inv.lead_source,
                "n_subjects": len(pids) or 1,
                "source": "prior_investigation",
            }
        )

    items.sort(key=lambda row: row.get("closed_at") or row.get("opened_at") or "", reverse=True)
    trimmed = items[:limit]
    return {
        "items": trimmed,
        "counts": {
            "total": len(trimmed),
            "cases": sum(1 for row in trimmed if row["kind"] == "case"),
            "investigations": sum(1 for row in trimmed if row["kind"] == "investigation"),
        },
        "current_run_id": current_run_id,
        "note": (
            "Prior SIU outcomes and closed or earlier-run cases. Labels are substantiated, "
            "education, referred, or unsubstantiated. The product recommends only."
        ),
    }
