from __future__ import annotations

from datetime import date, datetime
from typing import Any

from claimshield.db.models import Case, PipelineRun
from claimshield.queue.rank import recommendation_for


def screening_days_left(case: Case, *, today: date | None = None) -> int | None:
    if case.sla_due is None:
        return None
    due = case.sla_due.date() if isinstance(case.sla_due, datetime) else case.sla_due
    return (due - (today or date.today())).days


def why_rank(case: Case, factors: dict[str, Any] | None = None) -> dict[str, Any]:
    rec = recommendation_for(case.lane)
    composite = (factors or {}).get("composite")
    if case.lane == "harm_priority":
        return {
            "code": "harm_override",
            "recommendation": rec,
            "text": (
                f"Harm {case.harm} is at the CMS-style override. "
                "Beneficiary harm takes a reserved slice of hours before other factors."
            ),
        }
    if case.lane == "needs_evidence":
        return {
            "code": "evidence_floor",
            "recommendation": rec,
            "text": (
                f"High-impact concern with evidence strength {case.evidence_strength:.0%} "
                "below the 0.40 floor. Recommend prompt information gathering, not dismissal."
            ),
        }
    if case.lane == "overflow":
        return {
            "code": "tracked_backlog",
            "recommendation": rec,
            "text": (
                "Outside today's capacity or top-slot cap. The case stays open on a tracked "
                "backlog for reassessment when hours, evidence, or member impact change."
            ),
        }
    bits = []
    if composite is not None:
        bits.append(f"combined rank {float(composite):.0%}")
    bits.append(f"P(confirm) {case.p_confirm:.0%}")
    bits.append(f"${case.flagged_dollars:,.0f} flagged")
    bits.append(f"harm {case.harm} × {case.members_affected} members")
    return {
        "code": "multi_factor",
        "recommendation": rec,
        "text": "Recommended for today's queue on " + "; ".join(bits) + ".",
    }


def run_payload(run: PipelineRun, *, n_alerts: int, n_cases: int) -> dict[str, Any]:
    return {
        "run_id": run.run_id,
        "batch_id": run.batch_id,
        "status": run.status,
        "summary": run.summary,
        "n_alerts": n_alerts,
        "n_cases": n_cases,
        "horizon_days": run.horizon_days,
        "capacity_hours": (run.summary or {}).get("capacity_hours"),
        "screening_days": (run.summary or {}).get("screening_days"),
        "max_slots": (run.summary or {}).get("max_slots"),
        "member_weight": (run.summary or {}).get("member_weight"),
        "ranking_policy": (run.summary or {}).get("ranking_policy"),
    }
