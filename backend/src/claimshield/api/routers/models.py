from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from fastapi import APIRouter, Depends

from claimshield.api.deps import require
from claimshield.db.models import User
from claimshield.risk.artifact import default_path, load_artifact
from claimshield.risk.scoring import heuristic_summary

router = APIRouter(prefix="/api/v1/models", tags=["models"])


@router.get("/risk")
def risk_model(_: User = Depends(require("model:read"))) -> dict[str, Any]:
    """Registered risk model: version, label definitions, backtest metrics and calibration."""
    artifact = load_artifact(default_path())
    if artifact is None:
        return {**heuristic_summary(), "metrics": None}
    raw = json.loads(Path(artifact.path).read_text())
    return {
        **artifact.summary(),
        "features": {
            "hazard": artifact.hazard.provider_features,
            "confirm": artifact.confirm.features,
        },
        "data": raw.get("data"),
        "config": raw.get("config"),
        "metrics": raw.get("metrics"),
        "timing_seconds": raw.get("timing_seconds"),
    }
