"""Train, backtest and register the risk models.

Splits (leakage traps 1, 3 and 5):

* Worlds (generator seeds) are split into train / calibration / test groups. A ring lives in
  one world, so ring members can never straddle train and test.
* Rolling origin: for a test cutoff T, hazard rows are used for fitting only if their whole
  90-day label window plus a 30-day label lag closed by T (cutoff <= T - 120 days); case rows
  only if a 60-day investigation lag closed by T. Calibration uses the latest eligible slice
  of the calibration worlds. Test rows are the test worlds at T.
* The final artifact repeats the recipe with T = end of the window.
"""

from __future__ import annotations

import hashlib
import json
import time
from dataclasses import asdict, dataclass
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd
from sklearn.ensemble import HistGradientBoostingClassifier

from claimshield.risk.evaluate import (
    at_capacity,
    bands,
    capacity_select,
    probability_metrics,
    ranking,
    reliability,
)
from claimshield.risk.features import CASE_FEATURES, PROVIDER_FEATURES, assert_clean
from claimshield.risk.labels import HORIZONS, INTERVAL_DAYS
from claimshield.risk.model import (
    HazardModel,
    LogisticScorer,
    calibrate,
    fit_logistic,
    fit_platt,
    person_period,
    sigmoid,
)
from claimshield.risk.panel import Panel, build_panel
from claimshield.synth.profiles import PROFILES

ARTIFACT_SCHEMA = 1
HAZARD_LABEL_LAG_DAYS = 30
CASE_LABEL_LAG_DAYS = 60
PROVIDER_REVIEW_HOURS = 8.0  # base hours of a one-provider case in cases.builder
HAZARD_LABEL = (
    "P(the provider bills a planted fraudulent claim line within h days after the cutoff), "
    "h = 30/60/90, from one monthly discrete-time hazard. Features use only claims with service "
    "and received dates on or before the cutoff."
)
CONFIRM_LABEL = (
    "P(investigating a case built at the cutoff finds a planted scheme): a flagged line is "
    "planted, a subject billed planted lines by the cutoff, or a subject is a planted "
    "ring/shell/referral party. Hard negatives and detector noise are 0."
)


@dataclass(frozen=True)
class TrainConfig:
    profile: str = "panel"
    seed: int = 7
    n_worlds: int = 24
    capacity_hours: float = 40.0
    C: float = 0.5
    test_origin_months: tuple[int, ...] = (8, 9, 10, 11, 12)
    calibration_months: int = 2
    workers: int | None = None
    challenger: bool = True

    def world_seeds(self) -> list[int]:
        return [self.seed * 1000 + i for i in range(1, self.n_worlds + 1)]


@dataclass
class TrainedModels:
    hazard: HazardModel
    confirm: LogisticScorer


@dataclass
class WorldSplit:
    train: list[int]
    calibration: list[int]
    test: list[int]

    def as_dict(self) -> dict[str, list[int]]:
        return asdict(self)


def split_worlds(seeds: list[int]) -> WorldSplit:
    ordered = sorted(seeds)
    n_cal = max(1, round(0.2 * len(ordered)))
    n_test = max(1, round(0.2 * len(ordered)))
    n_train = len(ordered) - n_cal - n_test
    return WorldSplit(
        train=ordered[:n_train],
        calibration=ordered[n_train : n_train + n_cal],
        test=ordered[n_train + n_cal :],
    )


def hazard_fit_months(test_month: int) -> int:
    """Latest cutoff month whose 90-day window plus label lag closed by the test cutoff."""
    lag_months = (max(HORIZONS) + HAZARD_LABEL_LAG_DAYS) // INTERVAL_DAYS
    return test_month - lag_months


def case_fit_months(test_month: int) -> int:
    return test_month - CASE_LABEL_LAG_DAYS // INTERVAL_DAYS


def _rows(frame: pd.DataFrame, worlds: list[int], *, max_month: int, min_month: int = 0) -> pd.DataFrame:
    keep = frame["world"].isin(worlds) & frame["origin_month"].between(min_month, max_month)
    return frame[keep]


def fit_hazard(
    providers: pd.DataFrame,
    split: WorldSplit,
    test_month: int,
    cfg: TrainConfig,
    fit_worlds: list[int] | None = None,
) -> HazardModel:
    last = hazard_fit_months(test_month)
    usable = providers[~providers["held_out_provider"]]
    fit_rows = _rows(usable, fit_worlds or split.train, max_month=last)
    X, y = person_period(fit_rows, list(PROVIDER_FEATURES))
    assert_clean(X.columns)
    scorer = fit_logistic(X, y, C=cfg.C)
    cal_rows = _rows(usable, split.calibration, max_month=last, min_month=last - cfg.calibration_months + 1)
    Xc, yc = person_period(cal_rows, list(PROVIDER_FEATURES))
    calibrate(scorer, Xc, yc)
    return HazardModel(scorer=scorer)


def fit_confirm(
    cases: pd.DataFrame,
    split: WorldSplit,
    test_month: int,
    cfg: TrainConfig,
    fit_worlds: list[int] | None = None,
) -> LogisticScorer:
    last = case_fit_months(test_month)
    usable = cases[~cases["held_out_case"]]
    fit_rows = _rows(usable, fit_worlds or split.train, max_month=last)
    X = fit_rows[list(CASE_FEATURES)]
    assert_clean(X.columns)
    scorer = fit_logistic(X, fit_rows["y_confirm"].to_numpy(), C=cfg.C)
    cal_rows = _rows(usable, split.calibration, max_month=last, min_month=last - cfg.calibration_months + 1)
    return calibrate(scorer, cal_rows[list(CASE_FEATURES)], cal_rows["y_confirm"].to_numpy())


def _hgb(X: pd.DataFrame, y: np.ndarray, seed: int) -> HistGradientBoostingClassifier:
    model = HistGradientBoostingClassifier(
        max_iter=100, learning_rate=0.1, max_leaf_nodes=15, l2_regularization=1.0, random_state=seed
    )
    return model.fit(X, y)


def _hgb_logit(model: HistGradientBoostingClassifier, X: pd.DataFrame) -> np.ndarray:
    return np.asarray(model.decision_function(X), dtype=float)


def _challenger_hazard(
    providers: pd.DataFrame,
    split: WorldSplit,
    test_month: int,
    test: pd.DataFrame,
    cfg: TrainConfig,
) -> np.ndarray:
    last = hazard_fit_months(test_month)
    usable = providers[~providers["held_out_provider"]]
    X, y = person_period(_rows(usable, split.train, max_month=last), list(PROVIDER_FEATURES))
    model = _hgb(X, y, cfg.seed)
    Xc, yc = person_period(
        _rows(usable, split.calibration, max_month=last, min_month=last - cfg.calibration_months + 1),
        list(PROVIDER_FEATURES),
    )
    a, b = fit_platt(_hgb_logit(model, Xc), yc) or (1.0, 0.0)
    hz = []
    for k in range(1, 4):
        frame = test[list(PROVIDER_FEATURES)].copy()
        frame["interval_2"] = 1.0 if k == 2 else 0.0
        frame["interval_3"] = 1.0 if k == 3 else 0.0
        hz.append(sigmoid(a * _hgb_logit(model, frame) + b))
    return np.asarray(1.0 - np.cumprod(1.0 - np.column_stack(hz), axis=1), dtype=float)


def _challenger_confirm(
    cases: pd.DataFrame, split: WorldSplit, test_month: int, test: pd.DataFrame, cfg: TrainConfig
) -> np.ndarray:
    last = case_fit_months(test_month)
    usable = cases[~cases["held_out_case"]]
    fit_rows = _rows(usable, split.train, max_month=last)
    model = _hgb(fit_rows[list(CASE_FEATURES)], fit_rows["y_confirm"].to_numpy(), cfg.seed)
    cal = _rows(usable, split.calibration, max_month=last, min_month=last - cfg.calibration_months + 1)
    a, b = fit_platt(_hgb_logit(model, cal[list(CASE_FEATURES)]), cal["y_confirm"].to_numpy()) or (
        1.0,
        0.0,
    )
    return sigmoid(a * _hgb_logit(model, test[list(CASE_FEATURES)]) + b)


def backtest(panel: Panel, cfg: TrainConfig) -> dict[str, Any]:
    split = split_worlds(cfg.world_seeds())
    prov_scored: list[pd.DataFrame] = []
    case_scored: list[pd.DataFrame] = []
    held_prov: list[pd.DataFrame] = []
    held_case: list[pd.DataFrame] = []
    folds: list[dict[str, Any]] = []
    for month in cfg.test_origin_months:
        hazard = fit_hazard(panel.providers, split, month, cfg)
        confirm = fit_confirm(panel.cases, split, month, cfg)
        folds.append(
            {
                "test_origin_month": month,
                "hazard_fit_through_month": hazard_fit_months(month),
                "case_fit_through_month": case_fit_months(month),
                "hazard_calibrated": hazard.scorer.calibrated,
                "confirm_calibrated": confirm.calibrated,
            }
        )
        at_t = panel.providers[panel.providers["origin_month"] == month]
        test = at_t[at_t["world"].isin(split.test) & ~at_t["held_out_provider"]].copy()
        curve = hazard.cumulative(test)
        for i, h in enumerate(HORIZONS):
            test[f"model_f{h}"] = curve[:, i]
        if cfg.challenger:
            hgb = _challenger_hazard(panel.providers, split, month, test, cfg)
            for i, h in enumerate(HORIZONS):
                test[f"hgb_f{h}"] = hgb[:, i]
        prov_scored.append(test)

        unseen = at_t[at_t["world"].isin(split.test + split.calibration)].copy()
        unseen["model_f90"] = hazard.cumulative(unseen)[:, 2]
        held_prov.append(unseen)

        cases_t = panel.cases[panel.cases["origin_month"] == month]
        ctest = cases_t[cases_t["world"].isin(split.test) & ~cases_t["held_out_case"]].copy()
        ctest["model_p"] = confirm.predict(ctest)
        if cfg.challenger:
            ctest["hgb_p"] = _challenger_confirm(panel.cases, split, month, ctest, cfg)
        case_scored.append(ctest)
        cunseen = cases_t[cases_t["world"].isin(split.test + split.calibration)].copy()
        cunseen["model_p"] = confirm.predict(cunseen)
        held_case.append(cunseen)

    prov = pd.concat(prov_scored, ignore_index=True)
    prov["review_hours"] = PROVIDER_REVIEW_HOURS
    cases = pd.concat(case_scored, ignore_index=True)
    return {
        "split": split.as_dict(),
        "folds": folds,
        "hazard": _hazard_report(prov, cfg),
        "confirm": _confirm_report(cases, cfg),
        "held_out_scheme": _held_out_report(pd.concat(held_prov), pd.concat(held_case), cfg),
    }


def _score_block(
    frame: pd.DataFrame, y: str, score: str, cfg: TrainConfig, hours: str, probability: bool
) -> dict[str, Any]:
    yy = frame[y].to_numpy(dtype=int)
    ss = frame[score].to_numpy(dtype=float)
    block: dict[str, Any] = {**ranking(yy, ss)}
    if probability:
        block.update(probability_metrics(yy, ss))
    block.update(
        at_capacity(
            frame,
            score=score,
            label=y,
            hours=hours,
            groups=["world", "origin_month"],
            capacity=cfg.capacity_hours,
        )
    )
    return block


def _hazard_report(prov: pd.DataFrame, cfg: TrainConfig) -> dict[str, Any]:
    report: dict[str, Any] = {}
    for h in HORIZONS:
        obs = prov[prov[f"y_{h}"].notna()]
        scorers = {
            "model": (f"model_f{h}", True),
            "heuristic": (f"heuristic_f{h}", True),
            "rules_only": ("rules_only", False),
        }
        if f"hgb_f{h}" in obs:
            scorers["challenger_hgb"] = (f"hgb_f{h}", True)
        report[f"{h}d"] = {
            "n": len(obs),
            "base_rate": round(float(obs[f"y_{h}"].mean()), 4),
            **{
                name: _score_block(obs, f"y_{h}", col, cfg, "review_hours", prob)
                for name, (col, prob) in scorers.items()
            },
            "reliability_model": reliability(obs[f"y_{h}"].to_numpy(int), obs[f"model_f{h}"].to_numpy()),
            "bands_model": bands(obs[f"y_{h}"].to_numpy(int), obs[f"model_f{h}"].to_numpy()),
        }
    mono = (prov["model_f30"] <= prov["model_f60"] + 1e-12) & (prov["model_f60"] <= prov["model_f90"] + 1e-12)
    report["monotone_violations"] = int((~mono).sum())
    return report


def _confirm_report(cases: pd.DataFrame, cfg: TrainConfig) -> dict[str, Any]:
    scorers = {
        "model": ("model_p", True),
        "heuristic": ("heuristic_p", True),
        "rules_only": ("rules_only", False),
    }
    if "hgb_p" in cases:
        scorers["challenger_hgb"] = ("hgb_p", True)
    return {
        "n": len(cases),
        "base_rate": round(float(cases["y_confirm"].mean()), 4),
        **{name: _score_block(cases, "y_confirm", col, cfg, "hours", prob) for name, (col, prob) in scorers.items()},
        "reliability_model": reliability(cases["y_confirm"].to_numpy(int), cases["model_p"].to_numpy()),
        "bands_model": bands(cases["y_confirm"].to_numpy(int), cases["model_p"].to_numpy()),
    }


def _held_out_report(prov: pd.DataFrame, cases: pd.DataFrame, cfg: TrainConfig) -> dict[str, Any]:
    """S06 (ambulance) never enters fitting or calibration; score it here as an unseen type."""
    prov = prov.copy()
    prov["review_hours"] = PROVIDER_REVIEW_HOURS
    prov["is_target"] = prov["held_out_provider"] & (prov["all_y_90"] == 1)
    hits = n = 0
    pct: list[float] = []
    for _, grp in prov.groupby(["world", "origin_month"]):
        if not grp["is_target"].any():
            continue
        pick = capacity_select(grp, "model_f90", "review_hours", cfg.capacity_hours)
        ranks = grp["model_f90"].rank(pct=True)
        for idx in grp.index[grp["is_target"]]:
            n += 1
            hits += int(pick.at[idx])
            pct.append(float(ranks.at[idx]))
    held_cases = cases[cases["held_out_case"]]
    case_hits = 0
    for _, grp in cases.groupby(["world", "origin_month"]):
        if not grp["held_out_case"].any():
            continue
        pick = capacity_select(grp, "model_p", "hours", cfg.capacity_hours)
        case_hits += int(pick[grp["held_out_case"]].sum())
    return {
        "scheme": "S06 ambulance_impossible",
        "provider_rows_with_event_in_90d": n,
        "provider_recall_at_capacity_90d": round(hits / n, 4) if n else None,
        "provider_mean_percentile_90d": round(float(np.mean(pct)), 4) if pct else None,
        "cases": len(held_cases),
        "case_recall_at_capacity": round(case_hits / len(held_cases), 4) if len(held_cases) else None,
        "case_mean_p_confirm": round(float(held_cases["model_p"].mean()), 4) if len(held_cases) else None,
    }


def data_hash(panel: Panel) -> str:
    digest = hashlib.sha256()
    for frame in (panel.providers, panel.cases):
        ordered = frame.sort_values(["world", "origin_month"], kind="mergesort").reset_index(drop=True)
        digest.update(pd.util.hash_pandas_object(ordered, index=False).to_numpy().tobytes())
    return digest.hexdigest()[:16]


def fit_final(panel: Panel, cfg: TrainConfig) -> tuple[TrainedModels, WorldSplit]:
    split = split_worlds(cfg.world_seeds())
    end_month = PROFILES[cfg.profile].n_months
    fit_worlds = split.train + split.test
    hazard = fit_hazard(panel.providers, split, end_month, cfg, fit_worlds=fit_worlds)
    confirm = fit_confirm(panel.cases, split, end_month, cfg, fit_worlds=fit_worlds)
    return TrainedModels(hazard=hazard, confirm=confirm), split


def train(cfg: TrainConfig, out: Path | None = None) -> dict[str, Any]:
    started = time.perf_counter()
    panel = build_panel(cfg.profile, cfg.world_seeds(), workers=cfg.workers)
    built = time.perf_counter()
    report = backtest(panel, cfg)
    models, split = fit_final(panel, cfg)
    finished = time.perf_counter()
    dhash = data_hash(panel)
    config = {k: (list(v) if isinstance(v, tuple) else v) for k, v in asdict(cfg).items() if k != "workers"}
    version_src = json.dumps({"data": dhash, "config": config, "schema": ARTIFACT_SCHEMA}, sort_keys=True)
    artifact: dict[str, Any] = {
        "schema": ARTIFACT_SCHEMA,
        "model_version": "risk-" + hashlib.sha256(version_src.encode()).hexdigest()[:12],
        "training_data_hash": dhash,
        "trained_at": datetime.now(UTC).isoformat(timespec="seconds"),
        "config": config,
        "data": {
            "profile": cfg.profile,
            "worlds": split.as_dict(),
            "provider_rows": len(panel.providers),
            "case_rows": len(panel.cases),
            "hazard_label_lag_days": HAZARD_LABEL_LAG_DAYS,
            "case_label_lag_days": CASE_LABEL_LAG_DAYS,
        },
        "labels": {"hazard": HAZARD_LABEL, "confirm": CONFIRM_LABEL},
        "calibrated": bool(models.hazard.scorer.calibrated and models.confirm.calibrated),
        "hazard": {**models.hazard.to_dict(), "calibrated": models.hazard.scorer.calibrated},
        "confirm": {"scorer": models.confirm.to_dict(), "calibrated": models.confirm.calibrated},
        "metrics": report,
        "timing_seconds": {
            "build_panel": round(built - started, 1),
            "backtest_and_fit": round(finished - built, 1),
            "total": round(finished - started, 1),
        },
    }
    if out is not None:
        out.parent.mkdir(parents=True, exist_ok=True)
        out.write_text(json.dumps(artifact, indent=1, sort_keys=False) + "\n")
    return artifact
