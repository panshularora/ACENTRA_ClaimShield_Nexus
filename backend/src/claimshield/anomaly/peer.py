"""Peer-comparison anomaly layer (CMS FPS-style). Robust z and IQR fences."""

from __future__ import annotations

import numpy as np
import pandas as pd

from claimshield.rules.engine import AlertDraft


def evaluate_anomalies(tables: dict[str, pd.DataFrame]) -> list[AlertDraft]:
    alerts: list[AlertDraft] = []
    alerts.extend(_em_level_z(tables))
    alerts.extend(_home_health_iqr(tables))
    alerts.extend(_genetic_spike(tables))
    return alerts


def robust_z(value: float, peers: np.ndarray) -> float:
    if peers.size == 0:
        return 0.0
    med = float(np.median(peers))
    mad = float(np.median(np.abs(peers - med)))
    if mad < 1e-9:
        return 0.0
    return 0.6745 * (value - med) / mad


def _em_level_z(tables: dict[str, pd.DataFrame]) -> list[AlertDraft]:
    claims = tables["claim"][["claim_id", "billing_provider_id"]]
    lines = tables["claim_line"].merge(claims, on="claim_id")
    em = lines[lines.code.str.startswith("EM-EST-", na=False)]
    if em.empty:
        return []
    share = (em["code"] == "EM-EST-5").groupby(em["billing_provider_id"]).mean()
    values = share.to_numpy(dtype=float)
    out: list[AlertDraft] = []
    for provider_id, frac in share.items():
        z = robust_z(float(frac), values)
        if z < 2.5 or float(frac) < 0.4:
            continue
        hit = em[em.billing_provider_id == provider_id]
        out.append(
            AlertDraft(
                detector="anomaly",
                rule_id="A-EM-001",
                rule_version=1,
                entity_id=str(provider_id),
                entity_type="provider",
                line_ids=hit["line_id"].tolist()[:40],
                score=min(1.0, z / 6.0),
                evidence={"kind": "em_upcode_z", "share_level5": round(float(frac), 3), "robust_z": round(z, 3)},
            )
        )
    return out


def _home_health_iqr(tables: dict[str, pd.DataFrame]) -> list[AlertDraft]:
    claims = tables["claim"]
    hh = claims[claims.claim_type == "home_health"]
    if hh.empty:
        return []
    lines = tables["claim_line"].merge(hh[["claim_id", "billing_provider_id"]], on="claim_id")
    counts = lines.groupby("billing_provider_id").size().astype(float)
    q1, q3 = np.quantile(counts.to_numpy(), [0.25, 0.75])
    fence = q3 + 1.5 * (q3 - q1)
    out: list[AlertDraft] = []
    for provider_id, n in counts.items():
        if n <= fence or n < 20:
            continue
        hit = lines[lines.billing_provider_id == provider_id]
        out.append(
            AlertDraft(
                detector="anomaly",
                rule_id="A-HH-001",
                rule_version=1,
                entity_id=str(provider_id),
                entity_type="provider",
                line_ids=hit["line_id"].tolist()[:40],
                score=0.8,
                evidence={"kind": "hh_iqr", "visits": int(n), "fence": float(fence)},
            )
        )
    return out


def _genetic_spike(tables: dict[str, pd.DataFrame]) -> list[AlertDraft]:
    claims = tables["claim"][["claim_id", "billing_provider_id", "member_id"]]
    lines = tables["claim_line"].merge(claims, on="claim_id")
    gen = lines[lines.code == "LAB-GEN-01"]
    if gen.empty:
        return []
    counts = gen.groupby("billing_provider_id")["member_id"].nunique()
    out: list[AlertDraft] = []
    for provider_id, n in counts.items():
        if n < 12:
            continue
        hit = gen[gen.billing_provider_id == provider_id]
        out.append(
            AlertDraft(
                detector="anomaly",
                rule_id="A-GEN-001",
                rule_version=1,
                entity_id=str(provider_id),
                entity_type="provider",
                line_ids=hit["line_id"].tolist()[:40],
                score=0.85,
                evidence={"kind": "genetic_mill", "members": int(n)},
            )
        )
    return out
