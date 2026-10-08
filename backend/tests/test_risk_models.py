from __future__ import annotations

import json
from concurrent.futures import ProcessPoolExecutor
from pathlib import Path

import numpy as np
import pandas as pd
import pytest

from claimshield.pipeline.service import detect
from claimshield.risk.artifact import default_path, load_artifact
from claimshield.risk.features import PROVIDER_FEATURES
from claimshield.risk.labels import HORIZONS
from claimshield.risk.model import fit_platt, person_period, sigmoid
from claimshield.risk.panel import build_world
from claimshield.risk.train import TrainConfig, data_hash, fit_hazard, split_worlds


def _detect(tables, **kwargs):
    return detect(
        tables,
        horizon_days=60,
        recovery=0.5,
        harm_lambda=250.0,
        capacity_hours=40.0,
        **kwargs,
    )


@pytest.fixture(scope="module")
def artifact():
    loaded = load_artifact(default_path())
    assert loaded is not None, "data/models/risk_model.json should be committed and loadable"
    return loaded


def test_hazard_curve_is_monotone_for_any_input(artifact) -> None:
    rng = np.random.default_rng(11)
    X = pd.DataFrame(
        rng.normal(0, 3, size=(2000, len(PROVIDER_FEATURES))), columns=PROVIDER_FEATURES
    )
    curve = artifact.hazard.cumulative(X)
    assert curve.shape == (2000, len(HORIZONS))
    assert ((curve >= 0) & (curve <= 1)).all()
    assert (np.diff(curve, axis=1) >= -1e-12).all()


def test_person_period_rows_stop_at_the_event_and_at_censoring() -> None:
    rows = pd.DataFrame(
        {
            "event_interval": [2.0, None, None, 1.0],
            "censor_interval": [3, 3, 2, 3],
            **{f: [0.0] * 4 for f in PROVIDER_FEATURES},
        }
    )
    X, y = person_period(rows, list(PROVIDER_FEATURES))
    # event in k=2: rows k1(0), k2(1); no event: k1..k3; censored at 2: k1, k2; event k1: k1(1)
    assert len(X) == 2 + 3 + 2 + 1
    assert int(y.sum()) == 2
    assert set(X["interval_2"].unique()) <= {0.0, 1.0}


def test_platt_scaling_keeps_already_calibrated_scores() -> None:
    rng = np.random.default_rng(5)
    z = rng.normal(0, 1.5, size=20_000)
    y = (rng.random(z.size) < sigmoid(z)).astype(int)
    a, b = fit_platt(z, y)
    assert abs(a - 1.0) < 0.1
    assert abs(b) < 0.1
    assert fit_platt(z[:20], np.zeros(20, dtype=int)) is None


def test_committed_artifact_is_calibrated_and_beats_both_baselines(artifact) -> None:
    raw = json.loads(Path(artifact.path).read_text())
    metrics = raw["metrics"]
    assert artifact.calibrated
    assert metrics["hazard"]["monotone_violations"] == 0
    for horizon in ("30d", "60d", "90d"):
        block = metrics["hazard"][horizon]
        assert block["model"]["brier"] < block["heuristic"]["brier"]
        assert block["model"]["pr_auc"] > block["heuristic"]["pr_auc"]
        assert block["model"]["pr_auc"] > block["rules_only"]["pr_auc"]
        assert block["model"]["ece"] < 0.1
    confirm = metrics["confirm"]
    assert confirm["model"]["brier"] < confirm["heuristic"]["brier"]
    assert confirm["model"]["pr_auc"] > confirm["heuristic"]["pr_auc"]
    assert confirm["model"]["ece"] < 0.15


def test_panel_world_and_fit_are_deterministic_for_a_seed() -> None:
    first = build_world("panel", 4242)
    # The second copy is built in a worker process, which has its own string-hash seed, so
    # any dependence on set iteration order would show up as a different frame or data hash.
    with ProcessPoolExecutor(max_workers=1) as pool:
        second = pool.submit(build_world, "panel", 4242).result()
    pd.testing.assert_frame_equal(first.providers, second.providers)
    pd.testing.assert_frame_equal(first.cases, second.cases)
    assert data_hash(first) == data_hash(second)
    cfg = TrainConfig(seed=4, n_worlds=1, challenger=False)
    split = split_worlds([4242, 4242, 4242])
    one = fit_hazard(first.providers, split, 12, cfg)
    two = fit_hazard(second.providers, split, 12, cfg)
    assert one.scorer == two.scorer


def test_missing_or_broken_artifact_falls_back_to_the_labelled_heuristic(
    tmp_path, tiny_dataset
) -> None:
    assert load_artifact(tmp_path / "absent.json") is None
    broken = tmp_path / "broken.json"
    broken.write_text("{not json")
    assert load_artifact(broken) is None
    raw = json.loads(default_path().read_text())
    raw["confirm"]["scorer"]["features"] = ["something_else"]
    stale = tmp_path / "stale.json"
    stale.write_text(json.dumps(raw))
    assert load_artifact(stale) is None

    result = _detect(tiny_dataset.tables, use_trained_risk=False)
    assert result["risk_model"]["score_kind"] == "uncalibrated_heuristic"
    assert result["risk_model"]["calibrated"] is False
    for case in result["cases"]:
        assert case["risk"]["score_kind"] == "uncalibrated_heuristic"
        assert case["f30"] <= case["f60"] <= case["f90"]


def test_trained_scores_are_probabilities_with_factors(tiny_dataset, artifact) -> None:
    result = _detect(tiny_dataset.tables, risk_artifact=artifact)
    assert result["risk_model"]["model_version"] == artifact.model_version
    assert result["risk_model"]["score_kind"] == "trained_model"
    for case in result["cases"]:
        risk = case["risk"]
        assert 0.0 < case["p_confirm"] < 1.0
        assert risk["p_confirm_factors"], case["kinds"]
        assert {"feature", "label", "value", "contribution", "direction"} <= set(
            risk["p_confirm_factors"][0]
        )
        if case["f30"] is not None:
            assert 0.0 < case["f30"] <= case["f60"] <= case["f90"] < 1.0
            assert risk["risk_factors"]
            assert len(risk["monthly_hazards"]) == 3
