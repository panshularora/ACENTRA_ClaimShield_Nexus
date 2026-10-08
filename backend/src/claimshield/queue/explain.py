from __future__ import annotations

from datetime import date, datetime
from typing import Any

from claimshield.db.models import Case, PipelineRun


def screening_days_left(case: Case, *, today: date | None = None) -> int | None:
    if case.sla_due is None:
        return None
    due = case.sla_due.date() if isinstance(case.sla_due, datetime) else case.sla_due
    return (due - (today or date.today())).days


def why_rank(case: Case) -> dict[str, Any]:
    if case.lane == "harm_priority":
        return {
            "code": "harm_override",
            "text": (
                f"Harm {case.harm} is at the CMS-style override. "
                "Beneficiary harm takes a reserved slice of hours before dollar ranking."
            ),
        }
    if case.lane == "needs_evidence":
        return {
            "code": "evidence_floor",
            "text": (
                f"Evidence strength {case.evidence_strength:.0%} is below the 0.40 floor, "
                "so this case is not packed into today's hours."
            ),
        }
    if case.lane == "overflow":
        return {
            "code": "capacity",
            "text": "Outside remaining investigator hours after the knapsack fill.",
        }
    return {
        "code": "expected_value",
        "text": (
            f"Selected on expected value ${case.expected_value or 0:,.0f} "
            f"(P(confirm) {case.p_confirm:.0%} on ${case.flagged_dollars:,.0f} flagged)."
        ),
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
    }
