"""Detector semantics: fee schedules, ambulance trips, member-level opioid patterns, coding bypasses."""

from datetime import date

import pandas as pd

from claimshield.cases.workspace import validate_citations
from claimshield.pipeline.service import detect
from claimshield.rules.engine import _ambulance_overlap, _clone_billing, _doctor_shopping, _sex_implausible

DAY = date(2024, 5, 2)


def _claims(rows: list[dict]) -> dict[str, pd.DataFrame]:
    claims = pd.DataFrame(
        [{"claim_id": r["claim_id"], "member_id": r["member_id"], "billing_provider_id": r["provider"]} for r in rows]
    ).drop_duplicates("claim_id")
    lines = pd.DataFrame(
        [
            {
                "line_id": r["line_id"],
                "claim_id": r["claim_id"],
                "rendering_provider_id": r["provider"],
                "dos_from": r.get("dos", DAY),
                "code": r["code"],
                "paid": r.get("paid", 50.0),
                "minutes": r.get("minutes"),
                "modifiers": r.get("modifiers", []),
            }
            for r in rows
        ]
    )
    return {"claim": claims, "claim_line": lines}


def test_identical_fee_schedule_amounts_alone_do_not_fire_clone_billing() -> None:
    rows = []
    for p in range(30):
        for m in range(3):  # three members a day at the same fee everywhere
            rows.append(
                {
                    "line_id": f"L{p}-{m}",
                    "claim_id": f"C{p}-{m}",
                    "member_id": f"M{m}",
                    "provider": f"P{p}",
                    "code": "EM-EST-3",
                    "paid": 75.0,
                }
            )
    assert _clone_billing(_claims(rows)) == []
    rows += [
        {
            "line_id": f"X{m}",
            "claim_id": f"CX{m}",
            "member_id": f"MX{m}",
            "provider": "P-MILL",
            "code": "EM-EST-3",
            "paid": 75.0,
        }
        for m in range(14)
    ]
    alerts = _clone_billing(_claims(rows))
    assert [a.entity_id for a in alerts] == ["P-MILL"]
    assert alerts[0].evidence["members"] == 14
    assert "paid" not in alerts[0].evidence


def test_ambulance_base_plus_mileage_is_one_trip() -> None:
    one_trip = [
        {"line_id": "B1", "claim_id": "C1", "member_id": "M1", "provider": "AMB", "code": "A0427", "minutes": 95},
        {"line_id": "K1", "claim_id": "C1", "member_id": "M1", "provider": "AMB", "code": "A0425", "minutes": 95},
    ]
    assert _ambulance_overlap(_claims(one_trip)) == []
    two_trips = [
        *one_trip,
        {"line_id": "K2", "claim_id": "C2", "member_id": "M2", "provider": "AMB", "code": "A0425", "minutes": 90},
    ]
    alerts = _ambulance_overlap(_claims(two_trips))
    assert len(alerts) == 1
    assert alerts[0].evidence["trips"] == 2
    assert alerts[0].evidence["overlap_tested"] is False
    assert alerts[0].evidence["trips_without_base_line"] == 1


def test_sex_conflict_respects_kx_and_condition_code_45() -> None:
    rows = [
        {
            "line_id": "L1",
            "claim_id": "C1",
            "member_id": "F1",
            "provider": "P1",
            "code": "PROC-MALE-01",
            "modifiers": ["KX"],
        },
        {"line_id": "L2", "claim_id": "C2", "member_id": "F2", "provider": "P1", "code": "PROC-MALE-01"},
        {"line_id": "L3", "claim_id": "C3", "member_id": "F3", "provider": "P1", "code": "PROC-MALE-01"},
    ]
    tables = _claims(rows)
    tables["claim"]["condition_codes"] = [[], [], ["45"]]
    tables["member"] = pd.DataFrame([{"member_id": m, "sex": "F"} for m in ("F1", "F2", "F3")])
    alerts = _sex_implausible(tables)
    assert len(alerts) == 1
    assert alerts[0].line_ids == ["L2"]
    assert alerts[0].evidence["data_quality_check"] is True


def test_doctor_shopping_is_member_level_and_windowed(tiny_dataset) -> None:
    alerts = _doctor_shopping(tiny_dataset.tables)
    assert alerts
    members = set(tiny_dataset.tables["member"]["member_id"].astype(str))
    for alert in alerts:
        assert alert.entity_type == "member" and alert.entity_id in members
        assert alert.evidence["prescribers"] >= 4 and alert.evidence["pharmacies"] >= 4
        span = date.fromisoformat(alert.evidence["window_end"]) - date.fromisoformat(alert.evidence["window_start"])
        assert span.days < 180
        assert alert.evidence["fills"]
    spread_out = pd.DataFrame(
        [
            {
                "member_id": "M9",
                "prescriber_id": f"PR{i}",
                "pharmacy_id": f"PH{i}",
                "drug_class_syn": "opioid",
                "days_supply": 30,
                "qty": 90,
                "mme": 140,
                "fill_date": date(2023, 1, 1) + pd.Timedelta(days=200 * i),
            }
            for i in range(5)
        ]
    )
    tables = {**tiny_dataset.tables, "rx_fill": spread_out}
    assert _doctor_shopping(tables) == []


def test_member_level_cases_do_not_merge_into_provider_cases(tiny_dataset) -> None:
    result = detect(tiny_dataset.tables, horizon_days=60, recovery=0.5, capacity_hours=40, evidence_min=0.4)
    rx_cases = [c for c in result["cases"] if any(a.evidence.get("kind") == "doctor_shopping" for a in c["alerts"])]
    assert rx_cases
    for case in rx_cases:
        assert case["primary_entity_type"] == "member"
        assert {a.evidence.get("kind") for a in case["alerts"]} == {"doctor_shopping"}
        assert case["entity_ids"] == [case["primary_entity_id"]]


def test_brief_validator_drops_unresolved_citations() -> None:
    sections = [
        {
            "title": "A",
            "sentences": [
                {"text": "ok", "cites": [{"id": "alert:ALRT-1"}]},
                {"text": "bad", "cites": [{"id": "alert:ALRT-9"}]},
            ],
        },
        {"title": "B", "sentences": [{"text": "none", "cites": []}]},
        {"title": "C", "sentences": [{"text": "metric", "cites": [{"id": "metric:harm"}]}]},
    ]
    result = validate_citations(sections, alert_ids={"ALRT-1"}, precedents=[])
    assert (result["checked"], result["dropped"], result["cited"]) == (4, 2, 2)
    assert [s["title"] for s in sections] == ["A", "C"]
