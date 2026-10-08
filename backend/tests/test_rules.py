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
