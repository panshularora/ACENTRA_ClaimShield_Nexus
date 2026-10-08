from claimshield.pipeline.service import assign_lanes, detect
from claimshield.queue.rank import attach_rank_factors, weighted_composite


def _case(**kwargs) -> dict:
    base = {
        "case_id": "CASE-X",
        "harm": 2,
        "severity": 2,
        "members_affected": 2,
        "flagged_dollars": 5000.0,
        "evidence_strength": 0.7,
        "estimated_hours": 8.0,
        "p_confirm": 0.4,
        "f30": 0.2,
        "f60": 0.35,
        "f90": 0.45,
        "lane": "open",
    }
    base.update(kwargs)
    return base


def test_composite_is_not_money_or_evidence_alone() -> None:
    rich = _case(case_id="A", flagged_dollars=80_000, evidence_strength=0.35, harm=1, members_affected=1, severity=1)
    harm = _case(case_id="B", flagged_dollars=2_000, evidence_strength=0.55, harm=4, members_affected=6, severity=4)
    attach_rank_factors([rich, harm], horizon_days=60, member_weight=1.0)
    assert harm["composite"] > rich["composite"]
    weak = _case(case_id="C", flagged_dollars=1_000, evidence_strength=0.95, harm=1, members_affected=1, severity=1)
    attach_rank_factors([harm, weak], horizon_days=60, member_weight=1.0)
    assert harm["composite"] > weak["composite"]


def test_member_weight_changes_relative_rank() -> None:
    dollars = _case(case_id="D", flagged_dollars=90_000, harm=1, members_affected=1, evidence_strength=0.8, severity=2)
    members = _case(case_id="M", flagged_dollars=4_000, harm=3, members_affected=12, evidence_strength=0.8, severity=3)
    attach_rank_factors([dollars, members], horizon_days=60, member_weight=0.3)
    low_member = {c["case_id"]: c["composite"] for c in [dollars, members]}
    attach_rank_factors([dollars, members], horizon_days=60, member_weight=2.5)
    high_member = {c["case_id"]: c["composite"] for c in [dollars, members]}
    assert high_member["M"] - high_member["D"] > low_member["M"] - low_member["D"]


def test_slot_cap_keeps_overflow_open(tiny_dataset) -> None:
    result = detect(
        tiny_dataset.tables,
        horizon_days=60,
        recovery=0.5,
        harm_lambda=250.0,
        capacity_hours=200,
        max_slots=3,
        member_weight=1.0,
    )
    today = [c for c in result["cases"] if c["lane"] in {"harm_priority", "selected"}]
    harm_n = sum(1 for c in result["cases"] if c["lane"] == "harm_priority")
    assert len(today) <= max(3, harm_n)
    overflow = [c for c in result["cases"] if c["lane"] == "overflow"]
    assert overflow
    assert result["ranking_policy"]["overflow_is_dismissal"] is False
    assert result["ranking_policy"]["human_in_the_loop"] is True


def test_needs_evidence_stays_out_of_today_knapsack() -> None:
    cases = [
        _case(case_id="E", evidence_strength=0.2, harm=2, flagged_dollars=40_000),
        _case(case_id="S", evidence_strength=0.8, harm=2, flagged_dollars=8_000),
        _case(case_id="H", evidence_strength=0.9, harm=4, flagged_dollars=1_000),
    ]
    attach_rank_factors(cases, horizon_days=60, member_weight=1.0)
    assign_lanes(cases, capacity_hours=40, harm_capacity_share=0.35, evidence_min=0.4, max_slots=20)
    by_id = {c["case_id"]: c["lane"] for c in cases}
    assert by_id["H"] == "harm_priority"
    assert by_id["E"] == "needs_evidence"
    assert by_id["S"] == "selected"


def test_weights_renormalize_with_member_scale() -> None:
    scores = {"severity": 0.5, "exposure": 0.5, "member": 1.0, "evidence": 0.5, "urgency": 0.5}
    low, w_low = weighted_composite(scores, member_weight=0.5)
    high, w_high = weighted_composite(scores, member_weight=2.0)
    assert w_high["member"] > w_low["member"]
    assert abs(sum(w_high.values()) - 1.0) < 1e-3
    assert high > low
