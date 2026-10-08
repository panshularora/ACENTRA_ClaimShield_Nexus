"""The pre-model hand-set formulas, kept as a labelled fallback and as a backtest baseline.

They are used only when no trained artifact is available, and every score they produce is
labelled ``uncalibrated_heuristic`` on the API.
"""

from __future__ import annotations

from typing import Any

HEURISTIC_VERSION = "heuristic-v0"


def heuristic_hazard(p_confirm: float, harm: int) -> tuple[float, float, float, float]:
    """Constant monthly rate re-expressed as a CDF at 1/2/3 months: (monthly, f30, f60, f90)."""
    monthly = 0.05 + 0.28 * float(p_confirm) + 0.03 * int(harm)
    monthly = min(0.65, max(0.02, monthly))
    f = [round(1.0 - (1.0 - monthly) ** months, 3) for months in (1, 2, 3)]
    return round(monthly, 4), f[0], f[1], f[2]


def apply_heuristic_hazard(case: dict[str, Any]) -> tuple[float, float, float]:
    monthly, f30, f60, f90 = heuristic_hazard(float(case["p_confirm"]), int(case["harm"]))
    case["monthly_hazard"] = monthly
    return f30, f60, f90
