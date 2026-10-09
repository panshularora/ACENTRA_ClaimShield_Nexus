"""Score built cases with the registered models, or label the heuristic fallback.

Case 30/60/90 risk is the hazard curve of the case's riskiest provider subject (by 90-day
risk): the case is "active" if any of its subjects keeps billing planted-pattern lines.
Taking the max of monotone curves keeps 30 <= 60 <= 90.
"""

from __future__ import annotations

from datetime import date
from typing import Any

import numpy as np
import pandas as pd

from claimshield.pipeline.detectors import DetectorOutput
from claimshield.risk.artifact import RiskArtifact
from claimshield.risk.features import (
    FEATURE_LABELS,
    case_features,
    display_value,
    provider_features,
)
from claimshield.risk.heuristic import HEURISTIC_VERSION, apply_heuristic_hazard
from claimshield.risk.labels import HORIZONS
from claimshield.risk.snapshot import as_of, data_cutoff

TOP_FACTORS = 5
# Shown probabilities are clipped so the API never claims certainty; clipping is monotone, so
# 30 <= 60 <= 90 still holds.
PROB_FLOOR, PROB_CEIL = 0.001, 0.99
HEURISTIC_NOTE = (
    "No trained risk artifact was loaded. Suspicion and 30/60/90 are simple scores, "
    "not probabilities."
)


def shown(p: float) -> float:
    return round(min(PROB_CEIL, max(PROB_FLOOR, float(p))), 3)


def display_pct(p: float | None) -> str:
    """Human percent that never prints 100% — scores are not certainty."""
    if p is None:
        return "—"
    n = min(99, max(0, round(float(p) * 100)))
    return f"{n}%"


def heuristic_summary() -> dict[str, Any]:
    return {
        "score_kind": "uncalibrated_heuristic",
        "model_version": HEURISTIC_VERSION,
        "calibrated": False,
        "note": HEURISTIC_NOTE,
    }


def top_factors(contrib: pd.Series, values: pd.Series, k: int = TOP_FACTORS) -> list[dict[str, Any]]:
    order = contrib.abs().sort_values(ascending=False, kind="mergesort").index[:k]
    out = []
    for name in order:
        weight = float(contrib[name])
        if abs(weight) < 1e-3:
            continue
        out.append(
            {
                "feature": name,
                "label": FEATURE_LABELS.get(name, name),
                "value": display_value(name, float(values[name])),
                "contribution": round(weight, 3),
                "direction": "raises" if weight > 0 else "lowers",
            }
        )
    return out


def _set_heuristic(cases: list[dict[str, Any]]) -> None:
    for case in cases:
        case["f30"], case["f60"], case["f90"] = apply_heuristic_hazard(case)
        case["risk"] = {**heuristic_summary(), "risk_factors": [], "p_confirm_factors": []}


def score_cases(
    cases: list[dict[str, Any]],
    tables: dict[str, pd.DataFrame],
    detectors: DetectorOutput,
    *,
    artifact: RiskArtifact | None,
    cutoff: date | None = None,
) -> dict[str, Any]:
    """Write p_confirm, f30/f60/f90 and a ``risk`` block onto every case. Returns run metadata."""
    if artifact is None or not cases:
        _set_heuristic(cases)
        return heuristic_summary()
    asof = cutoff or data_cutoff(tables)
    snap = as_of(tables, asof)
    prov = provider_features(snap, detectors.alerts, detectors.graph, detectors.strong, asof)
    curves = pd.DataFrame(artifact.hazard.cumulative(prov), index=prov.index, columns=[f"f{h}" for h in HORIZONS])
    hazards = artifact.hazard.hazards(prov)
    hazard_contrib = artifact.hazard.contributions(prov)
    cf = case_features(cases)
    p_confirm = artifact.confirm.predict(cf)
    confirm_contrib = pd.DataFrame(artifact.confirm.contributions(cf), columns=artifact.confirm.features)
    info = artifact.summary()
    for i, case in enumerate(cases):
        subjects = [e for e in (case.get("entity_ids") or [case["primary_entity_id"]]) if e in curves.index]
        case["p_confirm"] = shown(p_confirm[i])
        block: dict[str, Any] = {
            "score_kind": "trained_model",
            "model_version": artifact.model_version,
            "calibrated": artifact.calibrated,
            "as_of": asof.isoformat(),
            "p_confirm_factors": top_factors(confirm_contrib.iloc[i], cf.iloc[i]),
        }
        if subjects:
            lead = max(subjects, key=lambda pid: (float(curves.at[pid, "f90"]), pid))
            row = int(np.flatnonzero(prov.index == lead)[0])
            case["f30"], case["f60"], case["f90"] = (shown(curves.at[lead, f"f{h}"]) for h in HORIZONS)
            block["risk_subject"] = lead
            block["monthly_hazards"] = [round(float(h), 4) for h in hazards[row]]
            block["risk_factors"] = top_factors(hazard_contrib.loc[lead], prov.loc[lead])
        else:
            # A subject outside the provider table (e.g. a member-level pattern): no hazard row.
            case["f30"] = case["f60"] = case["f90"] = None
            block["risk_subject"] = None
            block["monthly_hazards"] = None
            block["risk_factors"] = []
        case["risk"] = block
    return {**info, "as_of": asof.isoformat()}
