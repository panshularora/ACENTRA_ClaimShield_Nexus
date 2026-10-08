from collections import Counter

import pandas as pd

from claimshield.pipeline.service import detect
from claimshield.risk.heuristic import apply_heuristic_hazard
from claimshield.rules.engine import evaluate_rules


def _kinds(alerts) -> set[str]:
    return {a.evidence.get("kind") for a in alerts}


def _run(tiny_dataset, capacity_hours: float = 40.0):
    return detect(
        tiny_dataset.tables,
        horizon_days=60,
        recovery=0.5,
        capacity_hours=capacity_hours,
        harm_capacity_share=0.35,
        evidence_min=0.4,
    )


def test_evv_is_aggregated_not_flooded(tiny_dataset) -> None:
    alerts = evaluate_rules(tiny_dataset.tables)
    evv = [a for a in alerts if a.evidence.get("kind") == "evv_missing"]
    assert 1 <= len(evv) <= 5
    assert sum(len(a.line_ids) for a in evv) <= 20


def test_after_death_does_not_flag_duplicate_scheme(tiny_dataset) -> None:
    s01 = tiny_dataset.ground_truth[tiny_dataset.ground_truth.scheme_id == "S01"]
    s01_providers = set(s01["provider_id"].dropna().astype(str))
    s05 = tiny_dataset.ground_truth[tiny_dataset.ground_truth.scheme_id == "S05"]
    s05_providers = set(s05["provider_id"].dropna().astype(str))
    death = [a for a in evaluate_rules(tiny_dataset.tables) if a.evidence.get("kind") == "after_death"]
    death_entities = {a.entity_id for a in death}
    assert death_entities <= s05_providers
    assert not (death_entities & s01_providers)


def test_graph_catches_telefraud_ring(tiny_dataset) -> None:
    result = _run(tiny_dataset)
    g1 = tiny_dataset.ground_truth[tiny_dataset.ground_truth.scheme_id == "G1"].iloc[0]
    ring_ids = {str(x) for x in g1.entity_ids if str(x).startswith("PRV")}
    graph_alerts = [a for a in result["alerts"] if a.detector == "graph"]
    assert graph_alerts
    covered = set()
    multi = []
    for case in result["cases"]:
        entities = {str(e) for e in case["entity_ids"]}
        if len(entities) >= 2:
            multi.append(entities)
        covered |= entities
    assert ring_ids <= covered
    assert any(len(ring_ids & ents) >= 2 for ents in multi)


def test_stay_compression_detected(tiny_dataset) -> None:
    kinds = _kinds(evaluate_rules(tiny_dataset.tables))
    assert "stay_compression" in kinds


def test_override_hours_count_against_capacity(tiny_dataset) -> None:
    for hours in (8, 40, 120):
        result = _run(tiny_dataset, capacity_hours=hours)
        cap = result["capacity"]
        committed = sum(c["estimated_hours"] for c in result["cases"] if c["lane"] in {"harm_priority", "selected"})
        override = sum(c["estimated_hours"] for c in result["cases"] if c["lane"] == "harm_priority")
        assert abs(cap["capacity_used_hours"] - committed) < 0.11
        assert abs(cap["priority_override_hours"] - override) < 0.11
        # Selected work only fills what the override lane leaves; any overrun comes from overrides alone.
        assert cap["selected_hours"] <= max(0.0, hours - override) + 1e-6
        assert cap["over_capacity_hours"] == round(max(0.0, committed - hours), 1)
    low = _run(tiny_dataset, capacity_hours=40)
    high = _run(tiny_dataset, capacity_hours=120)
    lanes_low = Counter(c["lane"] for c in low["cases"])
    lanes_high = Counter(c["lane"] for c in high["cases"])
    assert lanes_high["selected"] > lanes_low["selected"]
    assert lanes_low["needs_evidence"] >= 1 or lanes_high["needs_evidence"] >= 1


def test_member_harm_comes_from_safety_signals(tiny_dataset) -> None:
    result = _run(tiny_dataset)
    for case in result["cases"]:
        kinds = {a.evidence.get("kind") for a in case["alerts"]}
        if case["harm"] >= 4:
            assert kinds & {"doctor_shopping", "inpatient_overlap", "daily_minutes_cap"}
        if kinds == {"after_death"}:
            assert case["harm"] < 4 and case["priority_override"] is True
        if case["priority_override"]:
            assert case["lane"] == "harm_priority"
            assert set(case["override_kinds"]) <= {"after_death", "excluded_party", "excluded_owner"}


def test_heuristic_fallback_hazard_is_monotonic() -> None:
    case = {"p_confirm": 0.4, "harm": 2}
    f30, f60, f90 = apply_heuristic_hazard(case)
    assert 0 < f30 <= f60 <= f90 < 1
    expected = 1 - (1 - case["monthly_hazard"]) ** 2
    assert abs(f60 - expected) < 5e-4


def test_scheme_recall_includes_g1_and_s19(tiny_dataset) -> None:
    result = _run(tiny_dataset)
    alert_entities: set[str] = set()
    alert_lines: set[str] = set()
    for alert in result["alerts"]:
        alert_entities.add(alert.entity_id)
        alert_entities.update(alert.related_entity_ids)
        alert_entities.update(str(x) for x in alert.evidence.get("peer_ids", []))
        alert_lines.update(alert.line_ids)
    fraud = tiny_dataset.ground_truth[tiny_dataset.ground_truth.is_fraud == True]  # noqa: E712
    missed = []
    for _, row in fraud.drop_duplicates("scheme_id").iterrows():
        pids = set()
        if row.provider_id is not None and not pd.isna(row.provider_id):
            pids.add(str(row.provider_id))
        if isinstance(row.entity_ids, list):
            pids.update(str(x) for x in row.entity_ids)
        lines = set(row.line_ids) if isinstance(row.line_ids, list) else set()
        hit = bool(pids & alert_entities) or bool(lines & alert_lines)
        if not hit:
            missed.append(row.scheme_id)
    assert "G1" not in missed
    assert "S19" not in missed
    assert len(missed) <= 2, missed
