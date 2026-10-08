"""Exclusion-list matching needs a second identifier and a date of service inside the window."""

from datetime import date

import pandas as pd

from claimshield.graph.detect import _excluded_owner
from claimshield.rules import leie
from claimshield.rules.engine import _excluded

EXCL_DATE = date(2024, 3, 1)


def _tables(*, excl_name=("Lauren", "Long"), npi="1234567893", dob=date(1971, 5, 2), address="12 Oak Street") -> dict:
    return {
        "exclusion_record": pd.DataFrame(
            [
                {
                    "excl_id": "EXC-1",
                    "firstname": excl_name[0],
                    "lastname": excl_name[1],
                    "busname": "",
                    "npi": npi,
                    "dob": dob,
                    "address": address,
                    "excl_date": EXCL_DATE,
                    "rein_date": None,
                }
            ]
        ),
        "provider": pd.DataFrame(
            [
                {"provider_id": "PRV-A", "npi_syn": "1234567893", "name": "Austin Howard", "location_id": "LOC-1"},
                {"provider_id": "PRV-B", "npi_syn": "1111111116", "name": "Shell Clinic LLC", "location_id": "LOC-1"},
            ]
        ),
        "location": pd.DataFrame([{"location_id": "LOC-1", "address_norm": "12 OAK ST"}]),
        "claim": pd.DataFrame(
            [
                {"claim_id": "C1", "billing_provider_id": "PRV-A", "member_id": "M1"},
                {"claim_id": "C2", "billing_provider_id": "PRV-A", "member_id": "M1"},
                {"claim_id": "C3", "billing_provider_id": "PRV-B", "member_id": "M2"},
            ]
        ),
        "claim_line": pd.DataFrame(
            [
                {
                    "line_id": "L-before",
                    "claim_id": "C1",
                    "rendering_provider_id": "PRV-A",
                    "dos_from": date(2024, 1, 5),
                },
                {
                    "line_id": "L-after",
                    "claim_id": "C2",
                    "rendering_provider_id": "PRV-A",
                    "dos_from": date(2024, 4, 5),
                },
                {
                    "line_id": "L-shell",
                    "claim_id": "C3",
                    "rendering_provider_id": "PRV-B",
                    "dos_from": date(2024, 5, 1),
                },
            ]
        ),
        "owner": pd.DataFrame(
            [{"owner_id": "OWN-1", "kind": "person", "name": "Lauren Long", "dob": date(1971, 5, 2)}]
        ),
        "ownership_link": pd.DataFrame([{"owner_id": "OWN-1", "provider_id": "PRV-B", "pct": 100}]),
    }


def test_npi_hit_with_a_different_name_is_not_an_excluded_party() -> None:
    assert _excluded(_tables(excl_name=("Lauren", "Long"))) == []


def test_npi_and_name_match_flags_only_lines_after_the_exclusion_date() -> None:
    alerts = _excluded(_tables(excl_name=("AUSTIN", "HOWARD, MD")))
    assert len(alerts) == 1
    assert alerts[0].line_ids == ["L-after"]
    assert alerts[0].evidence["match"] == "npi_and_name"
    assert alerts[0].evidence["excl_date"] == "2024-03-01"


def test_owner_match_needs_name_dob_and_address() -> None:
    hit = _excluded_owner(_tables())
    assert len(hit) == 1
    assert hit[0].evidence["match"] == "name_dob_address"
    assert hit[0].line_ids == ["L-shell"]
    assert _excluded_owner(_tables(dob=date(1965, 3, 12))) == []
    assert _excluded_owner(_tables(address="900 Elm Avenue")) == []


def test_name_normalization_is_tolerant_but_not_loose() -> None:
    record = {"firstname": "Jon", "lastname": "O'Neil", "busname": ""}
    assert leie.names_agree("JON ONEIL MD", record)
    assert not leie.names_agree("Joan Nelson", record)
