"""Multi-factor SIU ranking: severity, exposure, member impact, evidence, urgency."""

from __future__ import annotations

from datetime import date, datetime
from typing import Any

FACTOR_KEYS = ("severity", "exposure", "member", "evidence", "urgency")

DEFAULT_WEIGHTS: dict[str, float] = {
    "severity": 0.22,
    "exposure": 0.22,
    "member": 0.22,
    "evidence": 0.18,
    "urgency": 0.16,
}

FACTOR_LABELS: dict[str, str] = {
    "severity": "Scheme severity",
    "exposure": "Financial exposure",
    "member": "Member impact",
    "evidence": "Evidence strength",
    "urgency": "Urgency",
}

RECOMMEND_TODAY = "today_queue"
RECOMMEND_EVIDENCE = "gather_evidence"
RECOMMEND_BACKLOG = "tracked_backlog"

RANKING_NOTE = (
    "Today's queue is a fixed-weight mix of scheme severity, financial exposure, "
    "member impact, evidence strength and urgency, filled inside investigator hours. "
    "Suspicion and 30/60/90-day scores come from models trained on synthetic data. "
    "They rank work for a person. Cases outside today's slots stay open on a tracked backlog."
)


def _get(obj: Any, key: str, default: Any = None) -> Any:
    if isinstance(obj, dict):
        return obj.get(key, default)
    return getattr(obj, key, default)


def _p90(values: list[float]) -> float:
    if not values:
        return 1.0
    ordered = sorted(values)
    idx = min(len(ordered) - 1, max(0, round(0.9 * (len(ordered) - 1))))
    return max(float(ordered[idx]), 1.0)


def _horizon_risk(case: Any, horizon_days: int) -> float:
    if horizon_days <= 30:
        value = _get(case, "f30")
    elif horizon_days <= 60:
        value = _get(case, "f60")
    else:
        value = _get(case, "f90")
    return float(value or 0.0)


def _sla_urgency(case: Any, *, today: date | None = None) -> float:
    due = _get(case, "sla_due")
    if due is None:
        return 0.45
    if isinstance(due, datetime):
        due = due.date()
    left = (due - (today or date.today())).days
    if left <= 7:
        return 1.0
    if left <= 15:
        return 0.75
    if left <= 30:
        return 0.5
    return 0.3


def factor_scores(
    case: Any,
    *,
    horizon_days: int,
    dollar_scale: float,
    member_scale: float,
    today: date | None = None,
) -> dict[str, float]:
    harm = int(_get(case, "harm") or 0)
    severity = int(_get(case, "severity") or 0)
    members = max(1, int(_get(case, "members_affected") or 0))
    dollars = float(_get(case, "flagged_dollars") or 0.0)
    evidence = float(_get(case, "evidence_strength") or 0.0)
    return {
        "severity": round(min(1.0, max(harm, severity) / 4.0), 4),  # both scales run 1-4
        "exposure": round(min(1.0, dollars / max(dollar_scale, 1.0)), 4),
        "member": round(min(1.0, (harm * members) / max(member_scale, 1.0)), 4),
        "evidence": round(min(1.0, max(0.0, evidence)), 4),
        "urgency": round(
            min(1.0, 0.7 * _horizon_risk(case, horizon_days) + 0.3 * _sla_urgency(case, today=today)),
            4,
        ),
    }


def weighted_composite(
    scores: dict[str, float],
    *,
    member_weight: float = 1.0,
    weights: dict[str, float] | None = None,
) -> tuple[float, dict[str, float]]:
    base = dict(weights or DEFAULT_WEIGHTS)
    base["member"] = max(0.05, float(base["member"]) * max(0.25, float(member_weight)))
    total = sum(base.values()) or 1.0
    applied = {key: round(base[key] / total, 4) for key in FACTOR_KEYS}
    composite = sum(applied[key] * float(scores.get(key) or 0.0) for key in FACTOR_KEYS)
    return round(composite, 4), applied


def attach_rank_factors(
    cases: list[dict[str, Any]],
    *,
    horizon_days: int,
    member_weight: float = 1.0,
    today: date | None = None,
) -> None:
    dollar_scale = _p90([float(c.get("flagged_dollars") or 0.0) for c in cases])
    member_scale = _p90([int(c.get("harm") or 0) * max(1, int(c.get("members_affected") or 0)) for c in cases])
    for case in cases:
        scores = factor_scores(
            case,
            horizon_days=horizon_days,
            dollar_scale=dollar_scale,
            member_scale=member_scale,
            today=today,
        )
        composite, applied = weighted_composite(scores, member_weight=member_weight)
        case["composite"] = composite
        case["rank_factors"] = {
            **scores,
            "composite": composite,
            "weights": applied,
            "member_weight": round(float(member_weight), 3),
        }


def recommendation_for(lane: str) -> str:
    if lane in {"harm_priority", "selected"}:
        return RECOMMEND_TODAY
    if lane == "needs_evidence":
        return RECOMMEND_EVIDENCE
    return RECOMMEND_BACKLOG


def ranking_policy(*, max_slots: int, member_weight: float, capacity_hours: float) -> dict[str, Any]:
    return {
        "method": "multi_factor_capacity_knapsack",
        "factors": [{"key": key, "label": FACTOR_LABELS[key], "weight": DEFAULT_WEIGHTS[key]} for key in FACTOR_KEYS],
        "max_slots": int(max_slots),
        "member_weight": float(member_weight),
        "capacity_hours": float(capacity_hours),
        "human_in_the_loop": True,
        "overflow_is_dismissal": False,
        "note": RANKING_NOTE,
    }


def rank_pack_for_case(
    case: Any,
    *,
    horizon_days: int,
    peers: list[Any],
    member_weight: float = 1.0,
) -> dict[str, Any]:
    dollar_scale = _p90(
        [float(_get(c, "flagged_dollars") or 0.0) for c in peers] or [float(_get(case, "flagged_dollars") or 0.0)]
    )
    member_scale = _p90(
        [int(_get(c, "harm") or 0) * max(1, int(_get(c, "members_affected") or 0)) for c in peers]
        or [int(_get(case, "harm") or 0) * max(1, int(_get(case, "members_affected") or 0))]
    )
    scores = factor_scores(
        case,
        horizon_days=horizon_days,
        dollar_scale=dollar_scale,
        member_scale=member_scale,
    )
    composite, applied = weighted_composite(scores, member_weight=member_weight)
    return {
        **scores,
        "composite": composite,
        "weights": applied,
        "member_weight": round(float(member_weight), 3),
    }
