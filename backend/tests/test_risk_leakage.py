"""One guard test (or more) per leakage trap in the research brief, section 6.2."""

from __future__ import annotations

from dataclasses import replace
from datetime import date, timedelta

import numpy as np
import pandas as pd
import pytest

from claimshield.pipeline.detectors import run_detectors
from claimshield.risk.features import (
    CASE_FEATURES,
    PROVIDER_FEATURES,
    assert_clean,
    provider_features,
)
from claimshield.risk.labels import (
    HORIZONS,
    first_event_after,
    horizon_labels,
    index_ground_truth,
    interval_of,
)
from claimshield.risk.panel import origin_date
from claimshield.risk.snapshot import PROCESS_TABLES, as_of
from claimshield.risk.train import (
    CASE_LABEL_LAG_DAYS,
    HAZARD_LABEL_LAG_DAYS,
    TrainConfig,
    case_fit_months,
    fit_confirm,
    fit_hazard,
    hazard_fit_months,
    split_worlds,
)

CUTOFF = date(2024, 6, 1)


def _features_at(tables: dict[str, pd.DataFrame], cutoff: date = CUTOFF) -> pd.DataFrame:
    snap = as_of(tables, cutoff)
    det = run_detectors(snap)
    return provider_features(snap, det.alerts, det.graph, det.strong, cutoff)


# Trap 1: random splits -> rolling-origin, world-grouped splits only.


def test_fit_ignores_rows_after_the_purge_and_test_worlds(panel_small, small_config) -> None:
    split = split_worlds(small_config.world_seeds())
    month = 10
    hazard = fit_hazard(panel_small.providers, split, month, small_config)
    confirm = fit_confirm(panel_small.cases, split, month, small_config)

    rng = np.random.default_rng(0)
    providers = panel_small.providers.copy()
    late = (providers["origin_month"] > hazard_fit_months(month)) | providers["world"].isin(
        split.test
    )
    providers.loc[late, list(PROVIDER_FEATURES)] = rng.normal(
        size=(int(late.sum()), len(PROVIDER_FEATURES))
    )
    providers.loc[late, "event_interval"] = 1
    cases = panel_small.cases.copy()
    late_c = (cases["origin_month"] > case_fit_months(month)) | cases["world"].isin(split.test)
    cases.loc[late_c, "y_confirm"] = 1 - cases.loc[late_c, "y_confirm"]

    assert fit_hazard(providers, split, month, small_config).scorer == hazard.scorer
    assert fit_confirm(cases, split, month, small_config) == confirm


def test_world_split_is_disjoint_and_complete() -> None:
    seeds = TrainConfig().world_seeds()
    split = split_worlds(seeds)
    groups = [set(split.train), set(split.calibration), set(split.test)]
    assert sorted(seeds) == sorted(split.train + split.calibration + split.test)
    assert all(not (a & b) for i, a in enumerate(groups) for b in groups[i + 1 :])


# Trap 2: late claims -> a line counts only if dos <= t and received_date <= t.


def test_snapshot_requires_service_and_received_dates(tiny_dataset) -> None:
    tables = tiny_dataset.tables
    snap = as_of(tables, CUTOFF)
    ts = pd.Timestamp(CUTOFF)
    assert (pd.to_datetime(snap["claim_line"]["dos_from"]) <= ts).all()
    assert (pd.to_datetime(snap["claim"]["received_date"]) <= ts).all()
    merged = tables["claim_line"].merge(
        tables["claim"][["claim_id", "received_date"]], on="claim_id"
    )
    late = merged[
        (pd.to_datetime(merged["dos_from"]) <= ts) & (pd.to_datetime(merged["received_date"]) > ts)
    ]
    assert not late.empty, "fixture should contain service-before / received-after lines"
    assert not set(late["line_id"]) & set(snap["claim_line"]["line_id"])


def test_features_ignore_everything_after_the_cutoff(tiny_dataset) -> None:
    tables = {k: v.copy() for k, v in tiny_dataset.tables.items()}
    before = _features_at(tables)
    claims, lines = tables["claim"], tables["claim_line"]
    future_claim = pd.to_datetime(claims["received_date"]) > pd.Timestamp(CUTOFF)
    future_line = pd.to_datetime(lines["dos_from"]) > pd.Timestamp(CUTOFF)
    lines.loc[
        future_line | lines["claim_id"].isin(claims.loc[future_claim, "claim_id"]), "paid"
    ] *= 25
    extra = lines[future_line].copy()
    extra["line_id"] = extra["line_id"] + "-X"
    tables["claim_line"] = pd.concat([lines, extra], ignore_index=True)
    living = tables["member"]["date_of_death"].isna()
    tables["member"].loc[living, "date_of_death"] = CUTOFF + timedelta(days=10)
    after = _features_at(tables)
    pd.testing.assert_frame_equal(before, after)


def test_deaths_after_the_cutoff_are_not_yet_known(tiny_dataset) -> None:
    tables = dict(tiny_dataset.tables)
    tables["member"] = tables["member"].copy()
    tables["member"].loc[tables["member"].index[5], "date_of_death"] = CUTOFF + timedelta(days=3)
    snap = as_of(tables, CUTOFF)
    known = pd.to_datetime(snap["member"]["date_of_death"]).dropna()
    assert len(known) >= 1
    assert (known <= pd.Timestamp(CUTOFF)).all()
    assert pd.isna(snap["member"].loc[tables["member"].index[5], "date_of_death"])


# Trap 3: label dating -> labels come strictly after the cutoff; fits wait for labels to close.


def test_hazard_labels_start_after_the_cutoff_and_respect_censoring(tiny_dataset) -> None:
    gt = index_ground_truth(tiny_dataset.tables, tiny_dataset.ground_truth)
    firsts = first_event_after(gt, CUTOFF)
    assert firsts and all(d > CUTOFF for d in firsts.values())
    assert interval_of(CUTOFF, CUTOFF) is None
    assert interval_of(CUTOFF + timedelta(days=30), CUTOFF) == 1
    assert interval_of(CUTOFF + timedelta(days=31), CUTOFF) == 2
    end = CUTOFF + timedelta(days=45)
    labels = horizon_labels(None, CUTOFF, end)
    assert labels == {"y_30": 0.0, "y_60": None, "y_90": None}


@pytest.mark.parametrize("month", TrainConfig().test_origin_months)
def test_training_label_windows_close_before_the_test_cutoff(month: int) -> None:
    test_day = origin_date(month)
    last_hazard = origin_date(hazard_fit_months(month))
    assert last_hazard + timedelta(days=max(HORIZONS) + HAZARD_LABEL_LAG_DAYS) <= test_day
    assert origin_date(case_fit_months(month)) + timedelta(days=CASE_LABEL_LAG_DAYS) <= test_day


# Trap 4: process features (records requested, suspensions, outcomes) never reach features.


def test_investigation_tables_never_reach_features(tiny_dataset) -> None:
    snap = as_of(tiny_dataset.tables, CUTOFF)
    assert all(snap[name].empty for name in PROCESS_TABLES if name in snap)
    stripped = {k: v for k, v in tiny_dataset.tables.items() if k not in PROCESS_TABLES}
    pd.testing.assert_frame_equal(_features_at(tiny_dataset.tables), _features_at(stripped))


@pytest.mark.parametrize(
    "column",
    [
        "investigation_outcome",
        "records_requested",
        "payment_suspended",
        "lane",
        "decision_action",
        "prior_substantiated",
        "sla_due",
    ],
)
def test_process_columns_are_rejected(column: str) -> None:
    with pytest.raises(ValueError):
        assert_clean([column])


# Trap 5: ring members split across train and test -> worlds are the split unit.


def test_ring_members_live_in_one_world_and_one_split(panel_small, small_config) -> None:
    split = split_worlds(small_config.world_seeds())
    group_of = {w: g for g, ws in split.as_dict().items() for w in ws}
    rows = panel_small.providers
    by_provider = rows.groupby("provider_id")["world"].nunique()
    assert (by_provider == 1).all()
    assert rows["world"].map(group_of).notna().all()


# Trap 6: generator artefacts -> no ground-truth, ID, amount-rounding or lag features.


def test_feature_lists_are_clean_and_hold_no_ground_truth(tiny_dataset) -> None:
    assert_clean(PROVIDER_FEATURES)
    assert_clean(CASE_FEATURES)
    gt_cols = set(tiny_dataset.ground_truth.columns)
    assert not gt_cols & set(PROVIDER_FEATURES)
    assert not gt_cols & set(CASE_FEATURES)
    for banned in (
        "scheme_id",
        "is_fraud",
        "held_out",
        "provider_id",
        "paid_round_share",
        "received_lag_days",
        "enroll_tenure_days",
    ):
        with pytest.raises(ValueError):
            assert_clean([banned])


def test_features_do_not_depend_on_identifier_values(tiny_dataset) -> None:
    tables = {k: v.copy() for k, v in tiny_dataset.tables.items()}
    ids = tables["provider"]["provider_id"].astype(str).tolist()
    rng = np.random.default_rng(3)
    mapping = {pid: f"PRV-R{rng.integers(10**9, 10**10)}" for pid in ids}
    columns = {
        "provider": ["provider_id"],
        "claim": ["billing_provider_id"],
        "claim_line": ["rendering_provider_id", "ordering_provider_id"],
        "ownership_link": ["provider_id"],
        "contact_point": ["entity_id"],
        "referral": ["referring_id", "receiving_id"],
        "rx_fill": ["prescriber_id", "pharmacy_id"],
        "evv_visit": ["provider_id"],
        "investigation_subject": ["provider_id"],
    }
    for name, cols in columns.items():
        for col in cols:
            tables[name][col] = tables[name][col].map(lambda v: mapping.get(str(v), v))
    before = _features_at(tiny_dataset.tables)
    after = _features_at(tables)
    after.index = after.index.map({v: k for k, v in mapping.items()})
    pd.testing.assert_frame_equal(before.sort_index(), after.sort_index())


@pytest.fixture(scope="module")
def small_config() -> TrainConfig:
    return replace(TrainConfig(), seed=0, n_worlds=5, challenger=False)


@pytest.fixture(scope="module")
def panel_small(small_config):
    from claimshield.risk.panel import build_panel

    return build_panel(small_config.profile, small_config.world_seeds())
