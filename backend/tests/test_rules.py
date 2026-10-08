from claimshield.queue.knapsack import expected_value
from claimshield.rules.catalog import load_rule_catalog, stamp_catalog
from claimshield.rules.engine import evaluate_rules


def _kinds(alerts) -> set[str]:
    return {a.evidence.get("kind") for a in alerts}


def test_rules_catch_planted_hard_hits(tiny_dataset) -> None:
    alerts = evaluate_rules(tiny_dataset.tables)
    kinds = _kinds(alerts)
    for expected in {
        "duplicate",
        "ptp_pair",
        "unit_cap",
        "after_death",
        "daily_minutes_cap",
        "inpatient_overlap",
        "evv_missing",
        "excluded_party",
        "doctor_shopping",
        "sex_implausible",
        "pos_mismatch",
        "clone_billing",
        "stay_compression",
    }:
        assert expected in kinds, f"missing {expected}; have {kinds}"


def test_held_out_ambulance_still_has_rule_signal(tiny_dataset) -> None:
    alerts = evaluate_rules(tiny_dataset.tables)
    kinds = _kinds(alerts)
    assert "ambulance_overlap" in kinds or "unit_cap" in kinds


def test_rule_catalog_stamps_policy_refs(tiny_dataset) -> None:
    catalog = load_rule_catalog()
    assert catalog["R-DEATH-001"]["policy_ref"] == "OIG-DOD"
    assert catalog["R-EVV-001"]["policy_ref"] == "CURES-EVV"
    alerts = stamp_catalog(evaluate_rules(tiny_dataset.tables))
    death = next(a for a in alerts if a.rule_id == "R-DEATH-001")
    assert death.evidence["policy_ref"] == "OIG-DOD"
    assert death.evidence["rule_title"]


def test_harm_lambda_changes_expected_value() -> None:
    case = {
        "p_confirm": 0.4,
        "flagged_dollars": 1000.0,
        "harm": 4,
        "members_affected": 2,
    }
    low = expected_value(case, horizon_days=60, recovery=0.5, harm_lambda=50.0)
    high = expected_value(case, horizon_days=60, recovery=0.5, harm_lambda=250.0)
    assert high > low
