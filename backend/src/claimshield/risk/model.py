"""Logistic scorers with Platt calibration, stored as plain JSON (no pickle).

A logistic model is small enough to review in a diff, loads without executing code, and gives
exact per-feature contributions: contribution_j = a * coef_j * (x_j - mean_j) / scale_j on the
calibrated log-odds scale, relative to an average training row.
"""

from __future__ import annotations

from dataclasses import asdict, dataclass, field
from typing import Any

import numpy as np
import pandas as pd
from sklearn.linear_model import LogisticRegression

from claimshield.risk.labels import HORIZONS, INTERVAL_DAYS

INTERVAL_TERMS = ("interval_2", "interval_3")
MIN_CLASS_FOR_CALIBRATION = 5
Z_CLIP = 4.0


def sigmoid(z: np.ndarray) -> np.ndarray:
    return np.asarray(1.0 / (1.0 + np.exp(-np.clip(z, -35.0, 35.0))), dtype=float)


@dataclass
class LogisticScorer:
    features: list[str]
    mean: list[float]
    scale: list[float]
    coef: list[float]
    intercept: float
    platt_a: float = 1.0
    platt_b: float = 0.0
    calibrated: bool = False

    def _standardize(self, X: pd.DataFrame) -> np.ndarray:
        values = X.reindex(columns=self.features, fill_value=0.0).to_numpy(dtype=float)
        z = (values - np.asarray(self.mean)) / np.asarray(self.scale)
        # Winsorise: a case far outside the training range should not get an unbounded logit.
        return np.asarray(np.clip(z, -Z_CLIP, Z_CLIP), dtype=float)

    def raw_logit(self, X: pd.DataFrame) -> np.ndarray:
        return np.asarray(self._standardize(X) @ np.asarray(self.coef) + self.intercept, dtype=float)

    def logit(self, X: pd.DataFrame) -> np.ndarray:
        return self.platt_a * self.raw_logit(X) + self.platt_b

    def predict(self, X: pd.DataFrame) -> np.ndarray:
        return sigmoid(self.logit(X))

    def contributions(self, X: pd.DataFrame) -> np.ndarray:
        return np.asarray(self.platt_a * self._standardize(X) * np.asarray(self.coef), dtype=float)

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> LogisticScorer:
        return cls(**data)


def fit_logistic(X: pd.DataFrame, y: np.ndarray, *, C: float) -> LogisticScorer:
    features = list(X.columns)
    values = X.to_numpy(dtype=float)
    mean = values.mean(axis=0)
    scale = values.std(axis=0)
    scale[scale < 1e-9] = 1.0
    model = LogisticRegression(C=C, max_iter=5000)
    model.fit(np.clip((values - mean) / scale, -Z_CLIP, Z_CLIP), y.astype(int))
    return LogisticScorer(
        features=features,
        mean=[float(v) for v in mean],
        scale=[float(v) for v in scale],
        coef=[float(v) for v in model.coef_[0]],
        intercept=float(model.intercept_[0]),
    )


def fit_platt(raw_logit: np.ndarray, y: np.ndarray) -> tuple[float, float] | None:
    """Platt scaling on a held-out slice. None when either class is too rare to fit it."""
    y = y.astype(int)
    if y.sum() < MIN_CLASS_FOR_CALIBRATION or (1 - y).sum() < MIN_CLASS_FOR_CALIBRATION:
        return None
    model = LogisticRegression(C=1e6, max_iter=5000)
    model.fit(raw_logit.reshape(-1, 1), y)
    return float(model.coef_[0][0]), float(model.intercept_[0])


def calibrate(scorer: LogisticScorer, X: pd.DataFrame, y: np.ndarray) -> LogisticScorer:
    params = fit_platt(scorer.raw_logit(X), y)
    if params is not None:
        scorer.platt_a, scorer.platt_b = params
        scorer.calibrated = True
    return scorer


def person_period(rows: pd.DataFrame, features: list[str]) -> tuple[pd.DataFrame, np.ndarray]:
    """Expand provider-at-cutoff rows to one row per observed 30-day interval.

    Interval k is kept while the provider is still event-free at its start and the interval is
    fully inside the data window; the label is 1 only in the interval holding the first event.
    """
    parts: list[pd.DataFrame] = []
    labels: list[np.ndarray] = []
    event = rows["event_interval"].astype(float).fillna(np.inf).to_numpy()
    censor = rows["censor_interval"].to_numpy()
    for k in range(1, len(HORIZONS) + 1):
        keep = (censor >= k) & (event >= k)
        if not keep.any():
            continue
        part = rows.loc[keep, features].copy()
        for j, term in enumerate(INTERVAL_TERMS, start=2):
            part[term] = 1.0 if k == j else 0.0
        parts.append(part)
        labels.append((event[keep] == k).astype(int))
    if not parts:
        return pd.DataFrame(columns=[*features, *INTERVAL_TERMS]), np.array([], dtype=int)
    return pd.concat(parts, ignore_index=True), np.concatenate(labels)


@dataclass
class HazardModel:
    """One classifier for the monthly hazard h_k = P(event in interval k | none before)."""

    scorer: LogisticScorer
    interval_days: int = INTERVAL_DAYS
    horizons: list[int] = field(default_factory=lambda: list(HORIZONS))

    @property
    def provider_features(self) -> list[str]:
        return [f for f in self.scorer.features if f not in INTERVAL_TERMS]

    def hazards(self, X: pd.DataFrame) -> np.ndarray:
        """(n, 3) monthly hazards h1, h2, h3."""
        cols = []
        for k in range(1, len(self.horizons) + 1):
            frame = X.reindex(columns=self.provider_features, fill_value=0.0).copy()
            for j, term in enumerate(INTERVAL_TERMS, start=2):
                frame[term] = 1.0 if k == j else 0.0
            cols.append(self.scorer.predict(frame))
        return np.column_stack(cols)

    def cumulative(self, X: pd.DataFrame) -> np.ndarray:
        """(n, 3) risk at 30/60/90 days: F(k) = 1 - prod_{j<=k}(1 - h_j); monotone by design."""
        return 1.0 - np.cumprod(1.0 - self.hazards(X), axis=1)

    def contributions(self, X: pd.DataFrame) -> pd.DataFrame:
        """Per-feature log-odds contributions to the first-interval hazard."""
        frame = X.reindex(columns=self.provider_features, fill_value=0.0).copy()
        for term in INTERVAL_TERMS:
            frame[term] = 0.0
        contrib = self.scorer.contributions(frame)
        out = pd.DataFrame(contrib, columns=self.scorer.features, index=X.index)
        return out[self.provider_features]

    def to_dict(self) -> dict[str, Any]:
        return {
            "scorer": self.scorer.to_dict(),
            "interval_days": self.interval_days,
            "horizons": self.horizons,
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> HazardModel:
        return cls(
            scorer=LogisticScorer.from_dict(data["scorer"]),
            interval_days=int(data.get("interval_days", INTERVAL_DAYS)),
            horizons=[int(h) for h in data.get("horizons", HORIZONS)],
        )
