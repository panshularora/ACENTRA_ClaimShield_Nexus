from datetime import date, timedelta

import pandas as pd

from claimshield.synth.codes import CODE_SYSTEM_SYNTH
from claimshield.synth.generator import generate
from claimshield.synth.luhn import is_luhn


FORBIDDEN_FEATURE_COLS = {
    "scheme_id",
    "scheme_type",
    "held_out",
    "variant",
    "is_fraud",
    "ground_truth",
}

REQUIRED_SCHEMES = {
    "S01",
    "S02",
    "S03",
    "S04",
    "S05",
    "S06",
    "S07",
    "S08",
    "S09",
    "S10",
    "S11",
    "S12",
    "S13",
    "S14",
    "S15",
    "S16",
    "S17",
    "S18",
    "S19",
    "S20",
    "S21",
    "G1",
    "G2",
    "G3",
    "C1",
    "HN1",
    "HN2",
}


def test_same_seed_is_deterministic(tiny_dataset) -> None:
    again = generate("tiny", 7)
    assert tiny_dataset.tables["claim_line"]["line_id"].tolist() == again.tables["claim_line"]["line_id"].tolist()
    assert tiny_dataset.tables["provider"]["npi_syn"].tolist() == again.tables["provider"]["npi_syn"].tolist()


def test_no_cpt_code_system(tiny_dataset) -> None:
    systems = set(tiny_dataset.tables["claim_line"]["code_system"].unique())
    assert "CPT" not in systems
    assert CODE_SYSTEM_SYNTH in systems
    codes = " ".join(tiny_dataset.tables["claim_line"]["code"].astype(str).unique())
    assert "CPT" not in codes.upper()


def test_npis_are_luhn(tiny_dataset) -> None:
    for npi in tiny_dataset.tables["provider"]["npi_syn"]:
        assert is_luhn(str(npi))
        assert len(str(npi)) == 10


def test_ground_truth_locked_out_of_feature_tables(tiny_dataset) -> None:
    for name, frame in tiny_dataset.tables.items():
        overlap = FORBIDDEN_FEATURE_COLS.intersection(frame.columns)
        assert not overlap, f"{name} leaked {overlap}"
    assert "scheme_id" in tiny_dataset.ground_truth.columns
    assert tiny_dataset.ground_truth["scheme_id"].nunique() >= 20


def test_planted_schemes_and_hard_negatives(tiny_dataset) -> None:
    present = set(tiny_dataset.ground_truth["scheme_id"].unique())
    missing = REQUIRED_SCHEMES - present
    assert not missing, missing
    held = tiny_dataset.ground_truth[tiny_dataset.ground_truth.held_out == True]  # noqa: E712
    assert "S06" in set(held["scheme_id"])
    negatives = tiny_dataset.ground_truth[tiny_dataset.ground_truth.is_fraud == False]  # noqa: E712
    assert {"HN1", "HN2"} <= set(negatives["scheme_id"])


def test_data_card_states_design_knobs(tiny_dataset) -> None:
    card = tiny_dataset.data_card
    assert "design knobs" in card["base_rates"]
    assert "synthetic data" in card["limitations"]
    assert card["n_members"] == 120
    assert card["n_claim_lines"] > 2000


def _scheme_dates(ds, scheme_id: str) -> list:
    row = ds.ground_truth[ds.ground_truth.scheme_id == scheme_id].iloc[0]
    lines = ds.tables["claim_line"].set_index("line_id")
    return sorted(pd.Timestamp(d).date() for d in lines.loc[list(row.line_ids), "dos_from"])


def test_default_profiles_keep_fixed_scheme_offsets(tiny_dataset) -> None:
    start = date(2024, 1, 1)
    dates = _scheme_dates(tiny_dataset, "S10")
    assert dates[0] == start + timedelta(days=60)
    assert dates[-1] == start + timedelta(days=87)


def test_panel_profile_spreads_onsets_across_seeds() -> None:
    worlds = {seed: generate("panel", seed) for seed in (1, 2, 3)}
    onsets = {_scheme_dates(ds, "G1")[0] for ds in worlds.values()}
    assert len(onsets) == 3
    assert _scheme_dates(generate("panel", 2), "G1") == _scheme_dates(worlds[2], "G1")
    ring = _scheme_dates(worlds[1], "G1")
    assert (ring[-1] - ring[0]).days > 30


def test_panel_puts_held_out_ambulance_on_its_own_provider() -> None:
    ds = generate("panel", 4)
    gt = ds.ground_truth.set_index("scheme_id")
    assert gt.loc["S06", "provider_id"] != gt.loc["S04"].iloc[0]["provider_id"]
    assert bool(gt.loc["S06", "held_out"])
