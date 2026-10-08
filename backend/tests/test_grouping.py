import pandas as pd

from claimshield.cases.builder import build_cases
from claimshield.graph.build import build_graph, strong_component_map
from claimshield.pipeline.service import detect
from claimshield.rules.engine import AlertDraft


def test_comparison_peers_are_not_case_subjects(tiny_dataset) -> None:
    result = detect(
        tiny_dataset.tables,
        horizon_days=60,
        recovery=0.5,
        capacity_hours=40.0,
        harm_capacity_share=0.35,
        evidence_min=0.4,
    )
    for case in result["cases"]:
        subjects = {str(e) for e in case["entity_ids"]}
        held = set(case["grouping"]["comparison_peers_held_out"])
        assert subjects.isdisjoint(held)


def test_same_provider_alerts_share_a_case() -> None:
    a = AlertDraft(
        detector="rules",
        rule_id="R-DUP-001",
        rule_version=1,
        entity_id="PRV-A",
        entity_type="provider",
        line_ids=["LN-1"],
        score=1.0,
        evidence={"kind": "duplicate"},
    )
    b = AlertDraft(
        detector="anomaly",
        rule_id="A-EM-001",
        rule_version=1,
        entity_id="PRV-A",
        entity_type="provider",
        line_ids=["LN-2"],
        score=0.8,
        evidence={"kind": "em_upcode_z", "peer_ids": ["PRV-PEER-1", "PRV-PEER-2"]},
    )
    tables = {
        "claim": pd.DataFrame([{"claim_id": "CLM-1", "member_id": "MBR-1", "billing_provider_id": "PRV-A"}]),
        "claim_line": pd.DataFrame(
            [
                {"line_id": "LN-1", "claim_id": "CLM-1", "paid": 10.0},
                {"line_id": "LN-2", "claim_id": "CLM-1", "paid": 12.0},
            ]
        ),
        "investigation": pd.DataFrame(),
        "investigation_subject": pd.DataFrame(),
    }
    cases = build_cases([a, b], tables, {})
    assert len(cases) == 1
    assert cases[0]["entity_ids"] == ["PRV-A"]
    assert "PRV-PEER-1" not in cases[0]["entity_ids"]
    assert cases[0]["grouping"]["rule"] == "same_provider"
    assert "PRV-PEER-1" in cases[0]["grouping"]["comparison_peers_held_out"]


def test_ring_link_still_groups_providers(tiny_dataset) -> None:
    graph = build_graph(tiny_dataset.tables)
    strong = strong_component_map(graph)
    result = detect(
        tiny_dataset.tables,
        horizon_days=60,
        recovery=0.5,
        capacity_hours=40.0,
    )
    g1 = tiny_dataset.ground_truth[tiny_dataset.ground_truth.scheme_id == "G1"].iloc[0]
    ring_ids = {str(x) for x in g1.entity_ids if str(x).startswith("PRV")}
    multi = [{str(e) for e in case["entity_ids"]} for case in result["cases"] if len(case["entity_ids"]) >= 2]
    assert strong
    assert any(len(ring_ids & ents) >= 2 for ents in multi)
