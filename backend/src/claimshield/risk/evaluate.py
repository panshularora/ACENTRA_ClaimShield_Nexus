"""Backtest metrics: ranking, calibration, and precision/recall inside investigator capacity."""

from __future__ import annotations

from itertools import pairwise
from typing import Any

import numpy as np
import pandas as pd
from sklearn.metrics import average_precision_score, brier_score_loss, roc_auc_score


def _r(x: float | None, nd: int = 4) -> float | None:
    return None if x is None or not np.isfinite(x) else round(float(x), nd)


def ranking(y: np.ndarray, score: np.ndarray) -> dict[str, float | None]:
    if len(np.unique(y)) < 2:
        return {"pr_auc": None, "roc_auc": None}
    return {
        "pr_auc": _r(average_precision_score(y, score)),
        "roc_auc": _r(roc_auc_score(y, score)),
    }


def reliability(y: np.ndarray, p: np.ndarray, bins: int = 10) -> list[dict[str, float]]:
    """Equal-frequency bins: mean predicted vs observed rate."""
    if len(p) == 0:
        return []
    order = np.argsort(p, kind="mergesort")
    out = []
    for chunk in np.array_split(order, min(bins, len(p))):
        if len(chunk) == 0:
            continue
        out.append(
            {
                "mean_predicted": round(float(p[chunk].mean()), 4),
                "observed_rate": round(float(y[chunk].mean()), 4),
                "n": len(chunk),
            }
        )
    return out


BAND_EDGES = (0.0, 0.25, 0.5, 0.75, 0.9, 0.99, 1.0)


def bands(y: np.ndarray, p: np.ndarray, edges: tuple[float, ...] = BAND_EDGES) -> list[dict[str, Any]]:
    """Fixed probability bands [lo, hi): count, mean predicted and observed rate.

    Used to judge display cut-offs (for example the queue's 25/50/75% placeholders)
    against what the backtest actually observed in each band. The top band includes 1.0.
    """
    out: list[dict[str, Any]] = []
    for i, (lo, hi) in enumerate(pairwise(edges)):
        last = i == len(edges) - 2
        mask = (p >= lo) & ((p <= hi) if last else (p < hi))
        n = int(mask.sum())
        out.append(
            {
                "band": [lo, hi],
                "n": n,
                "mean_predicted": _r(float(p[mask].mean())) if n else None,
                "observed_rate": _r(float(y[mask].mean())) if n else None,
            }
        )
    return out


def ece(y: np.ndarray, p: np.ndarray, bins: int = 10) -> float | None:
    table = reliability(y, p, bins)
    if not table:
        return None
    n = sum(b["n"] for b in table)
    return _r(sum(b["n"] * abs(b["mean_predicted"] - b["observed_rate"]) for b in table) / n)


def probability_metrics(y: np.ndarray, p: np.ndarray) -> dict[str, Any]:
    return {"brier": _r(brier_score_loss(y, np.clip(p, 0, 1))), "ece": ece(y, p)}


def capacity_select(frame: pd.DataFrame, score: str, hours: str, capacity: float) -> pd.Series:
    """Greedy top-down fill: take the highest score that still fits the remaining hours."""
    chosen = pd.Series(False, index=frame.index)
    left = float(capacity)
    for idx in frame.sort_values(score, ascending=False, kind="mergesort").index:
        need = float(frame.at[idx, hours])
        if need <= left:
            chosen.at[idx] = True
            left -= need
    return chosen


def at_capacity(
    frame: pd.DataFrame,
    *,
    score: str,
    label: str,
    hours: str,
    groups: list[str],
    capacity: float,
) -> dict[str, Any]:
    """Precision and recall of the capacity-filled pick, pooled over groups (world x cutoff)."""
    tp = selected = positives = 0
    for _, grp in frame.groupby(groups, sort=True):
        pick = capacity_select(grp, score, hours, capacity)
        y = grp[label].astype(int)
        tp += int((y[pick] == 1).sum())
        selected += int(pick.sum())
        positives += int(y.sum())
    return {
        "precision_at_capacity": _r(tp / selected) if selected else None,
        "recall_at_capacity": _r(tp / positives) if positives else None,
        "selected": selected,
        "true_positives": tp,
        "positives": positives,
    }
