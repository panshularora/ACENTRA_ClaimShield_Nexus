"""Load the registered risk-model artifact (plain JSON written by ``risk.train``)."""

from __future__ import annotations

import json
import logging
from dataclasses import dataclass
from functools import lru_cache
from pathlib import Path
from typing import Any

from claimshield.core.config import Settings, get_settings
from claimshield.risk.features import CASE_FEATURES, PROVIDER_FEATURES
from claimshield.risk.model import INTERVAL_TERMS, HazardModel, LogisticScorer

log = logging.getLogger(__name__)
SUPPORTED_SCHEMA = 1
ARTIFACT_NAME = "risk_model.json"


@dataclass(frozen=True)
class RiskArtifact:
    model_version: str
    calibrated: bool
    hazard: HazardModel
    confirm: LogisticScorer
    path: str
    card: dict[str, Any]

    def summary(self) -> dict[str, Any]:
        return {
            "score_kind": "trained_model",
            "model_version": self.model_version,
            "calibrated": self.calibrated,
            **self.card,
        }


def default_path(settings: Settings | None = None) -> Path:
    cfg = settings or get_settings()
    return cfg.risk_model_path or (cfg.data_dir / "models" / ARTIFACT_NAME)


def _card(raw: dict[str, Any]) -> dict[str, Any]:
    metrics = raw.get("metrics") or {}
    hazard = metrics.get("hazard") or {}
    confirm = metrics.get("confirm") or {}

    def headline(block: dict[str, Any]) -> dict[str, Any]:
        model = block.get("model") or {}
        keys = ("pr_auc", "roc_auc", "brier", "ece", "precision_at_capacity", "recall_at_capacity")
        return {k: model.get(k) for k in keys}

    return {
        "training_data_hash": raw.get("training_data_hash"),
        "trained_at": raw.get("trained_at"),
        "labels": raw.get("labels"),
        "training_profile": (raw.get("data") or {}).get("profile"),
        "backtest": {
            "hazard_90d": headline(hazard.get("90d") or {}),
            "confirm": headline(confirm),
        },
        "synthetic_only": True,
    }


def parse_artifact(raw: dict[str, Any], path: str) -> RiskArtifact:
    if int(raw.get("schema", -1)) != SUPPORTED_SCHEMA:
        raise ValueError(f"unsupported risk artifact schema {raw.get('schema')}")
    hazard = HazardModel.from_dict(raw["hazard"])
    confirm = LogisticScorer.from_dict(raw["confirm"]["scorer"])
    if hazard.scorer.features != [*PROVIDER_FEATURES, *INTERVAL_TERMS]:
        raise ValueError("hazard feature list does not match this code version")
    if confirm.features != list(CASE_FEATURES):
        raise ValueError("confirm feature list does not match this code version")
    return RiskArtifact(
        model_version=str(raw["model_version"]),
        calibrated=bool(hazard.scorer.calibrated and confirm.calibrated),
        hazard=hazard,
        confirm=confirm,
        path=path,
        card=_card(raw),
    )


@lru_cache(maxsize=4)
def _load_cached(path: str, mtime_ns: int) -> RiskArtifact | None:
    _ = mtime_ns  # part of the cache key: a retrained file is picked up without a restart
    try:
        return parse_artifact(json.loads(Path(path).read_text()), path)
    except (OSError, ValueError, KeyError, TypeError) as exc:
        log.warning("risk artifact %s not usable (%s); using the uncalibrated heuristic", path, exc)
        return None


def load_artifact(path: Path | None = None) -> RiskArtifact | None:
    target = path or default_path()
    try:
        mtime = target.stat().st_mtime_ns
    except OSError:
        log.info("no risk artifact at %s; using the uncalibrated heuristic", target)
        return None
    return _load_cached(str(target), mtime)
