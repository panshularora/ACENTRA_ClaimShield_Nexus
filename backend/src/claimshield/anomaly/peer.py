"""Peer-comparison anomaly layer. Compare like with like; never treat a z-score as fraud."""

from __future__ import annotations

from typing import Any

import numpy as np
import pandas as pd

from claimshield.rules.engine import AlertDraft

MIN_PEERS_TO_FLAG = 8
MIN_PEERS_RELAXED = 5
Z_FLAG = 2.5
Z_FLAG_LIMITED = 3.2


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
        if abs(value - med) < 1e-9:
            return 0.0
        return 6.0 if value > med else -6.0
    return 0.6745 * (value - med) / mad


def _providers(tables: dict[str, pd.DataFrame]) -> pd.DataFrame:
    cols = ["provider_id", "specialty", "kind", "rural", "service_line", "location_id"]
    frame = tables["provider"][cols].copy()
    frame["provider_id"] = frame["provider_id"].astype(str)
    frame["rural"] = frame["rural"].fillna(False).astype(bool)
    return frame


def select_peer_group(
    providers: pd.DataFrame,
    provider_id: str,
    eligible: set[str] | None = None,
) -> dict[str, Any]:
    """Widen specialty → type → geography until the group is large enough to compare."""
    row = providers[providers.provider_id == str(provider_id)]
    if row.empty:
        return {
            "peer_ids": [],
            "n_peers": 0,
            "dimensions_used": [],
            "selection": "provider not found",
            "relaxed": True,
            "confidence": "insufficient",
            "limitation": "Provider is missing from the peer table.",
        }
    rec = row.iloc[0]
    pool = providers
    if eligible is not None:
        pool = pool[pool.provider_id.isin(eligible)]
    attempts: list[tuple[list[str], str]] = [
        (["specialty", "kind", "rural"], "specialty, provider type, and geography (rural/urban)"),
        (["specialty", "kind"], "specialty and provider type; geography relaxed"),
        (["specialty"], "specialty only; type and geography relaxed"),
    ]
    chosen: pd.DataFrame | None = None
    dims: list[str] = []
    label = ""
    for dims, label in attempts:  # noqa: B007 - the last attempted tier labels the comparison below
        mask = pd.Series(True, index=pool.index)
        if "specialty" in dims:
            mask &= pool.specialty == rec.specialty
        if "kind" in dims:
            mask &= pool.kind == rec.kind
        if "rural" in dims:
            mask &= pool.rural == rec.rural
        hit = pool.loc[mask]
        others = hit[hit.provider_id != str(provider_id)]
        if len(others) >= MIN_PEERS_TO_FLAG:
            chosen = others
            break
        chosen = others
    assert chosen is not None
    n = len(chosen)
    relaxed = "rural" not in dims or n < MIN_PEERS_TO_FLAG
    if n < MIN_PEERS_RELAXED:
        confidence = "insufficient"
        limitation = (
            f"Only {n} peer(s) share this specialty/type/geography mix. "
            "The comparison is not used to auto-flag the provider."
        )
    elif n < MIN_PEERS_TO_FLAG or relaxed:
        confidence = "limited"
        limitation = (
            f"Peer group has {n} providers after relaxing dimensions ({label}). "
            "A rural or low-volume cell can make the range unstable."
        )
    else:
        confidence = "adequate"
        limitation = ""
    return {
        "peer_ids": chosen.provider_id.astype(str).tolist(),
        "n_peers": n,
        "dimensions_used": dims,
        "selection": label,
        "specialty": rec.specialty,
        "provider_type": rec.kind,
        "geography": "rural" if bool(rec.rural) else "urban",
        "service_line": rec.service_line,
        "relaxed": relaxed,
        "confidence": confidence,
        "limitation": limitation,
        "rural": bool(rec.rural),
    }


def _range_stats(values: np.ndarray) -> dict[str, float]:
    if values.size == 0:
        return {"peer_median": 0.0, "peer_q1": 0.0, "peer_q3": 0.0, "peer_min": 0.0, "peer_max": 0.0}
    q1, q3 = np.quantile(values, [0.25, 0.75])
    return {
        "peer_median": round(float(np.median(values)), 4),
        "peer_q1": round(float(q1), 4),
        "peer_q3": round(float(q3), 4),
        "peer_min": round(float(np.min(values)), 4),
        "peer_max": round(float(np.max(values)), 4),
    }


def _should_flag(*, z: float, n_peers: int, confidence: str) -> bool:
    if confidence == "insufficient" or n_peers < MIN_PEERS_RELAXED:
        return False
    if confidence == "limited":
        return z >= Z_FLAG_LIMITED
    return z >= Z_FLAG


def _em_level_z(tables: dict[str, pd.DataFrame]) -> list[AlertDraft]:
    providers = _providers(tables)
    claims = tables["claim"][["claim_id", "billing_provider_id"]]
    lines = tables["claim_line"].merge(claims, on="claim_id")
    em = lines[lines.code.str.startswith("EM-EST-", na=False)]
    if em.empty:
        return []
    share = (em["code"] == "EM-EST-5").groupby(em["billing_provider_id"]).mean()
    share.index = share.index.astype(str)
    eligible = set(share.index)
    out: list[AlertDraft] = []
    for provider_id, frac in share.items():
        group = select_peer_group(providers, str(provider_id), eligible)
        peer_vals = np.array(
            [float(share[p]) for p in group["peer_ids"] if p in share.index],
            dtype=float,
        )
        group["n_peers"] = int(peer_vals.size)
        stats = _range_stats(peer_vals)
        z = robust_z(float(frac), peer_vals)
        if float(frac) < 0.4 or not _should_flag(z=z, n_peers=group["n_peers"], confidence=group["confidence"]):
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
                evidence={
                    "kind": "em_upcode_z",
                    "approach": "behavioral_anomaly",
                    "metric": "share of highest-level office visits",
                    "provider_value": round(float(frac), 4),
                    "robust_z": round(z, 3),
                    "review_reason": (
                        "Level-5 share is high versus providers with the same specialty, type, "
                        "and (when possible) rural/urban geography."
                    ),
                    **stats,
                    "peer_group": group,
                },
            )
        )
    return out


def _home_health_iqr(tables: dict[str, pd.DataFrame]) -> list[AlertDraft]:
    providers = _providers(tables)
    claims = tables["claim"]
    hh = claims[claims.claim_type == "home_health"]
    if hh.empty:
        return []
    lines = tables["claim_line"].merge(hh[["claim_id", "billing_provider_id"]], on="claim_id")
    counts = lines.groupby("billing_provider_id").size().astype(float)
    counts.index = counts.index.astype(str)
    eligible = set(counts.index)
    out: list[AlertDraft] = []
    for provider_id, n in counts.items():
        group = select_peer_group(providers, str(provider_id), eligible)
        peer_vals = np.array(
            [float(counts[p]) for p in group["peer_ids"] if p in counts.index],
            dtype=float,
        )
        group["n_peers"] = int(peer_vals.size)
        stats = _range_stats(peer_vals)
        fence = stats["peer_q3"] + 1.5 * (stats["peer_q3"] - stats["peer_q1"])
        z = robust_z(float(n), peer_vals)
        if float(n) < 20 or float(n) <= fence:
            continue
        if group["confidence"] == "insufficient" or group["n_peers"] < MIN_PEERS_RELAXED:
            continue
        if group["confidence"] == "limited" and float(n) < fence * 1.35:
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
                score=min(1.0, 0.55 + 0.08 * z),
                evidence={
                    "kind": "hh_iqr",
                    "approach": "behavioral_anomaly",
                    "metric": "home-health visits in this window",
                    "provider_value": int(n),
                    "fence": round(float(fence), 2),
                    "robust_z": round(z, 3),
                    "review_reason": (
                        "Home-health visit volume sits well above similar providers in the same specialty and setting."
                    ),
                    **stats,
                    "peer_group": group,
                },
            )
        )
    return out


def _genetic_spike(tables: dict[str, pd.DataFrame]) -> list[AlertDraft]:
    providers = _providers(tables)
    cols = [c for c in ("claim_id", "billing_provider_id", "member_id") if c in tables["claim"].columns]
    claims = tables["claim"][cols]
    if "member_id" not in claims.columns:
        return []
    lines = tables["claim_line"].merge(claims, on="claim_id")
    gen = lines[lines.code == "LAB-GEN-01"]
    if gen.empty:
        return []
    counts = gen.groupby("billing_provider_id")["member_id"].nunique().astype(float)
    counts.index = counts.index.astype(str)
    eligible = set(counts.index)
    out: list[AlertDraft] = []
    for provider_id, n in counts.items():
        group = select_peer_group(providers, str(provider_id), eligible)
        peer_vals = np.array(
            [float(counts[p]) for p in group["peer_ids"] if p in counts.index],
            dtype=float,
        )
        group["n_peers"] = int(peer_vals.size)
        stats = _range_stats(peer_vals)
        z = robust_z(float(n), peer_vals)
        if float(n) < 12:
            continue
        if group["confidence"] == "insufficient" or group["n_peers"] < MIN_PEERS_RELAXED:
            continue
        if group["confidence"] == "limited" and z < Z_FLAG_LIMITED:
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
                score=min(1.0, 0.5 + 0.1 * z),
                evidence={
                    "kind": "genetic_mill",
                    "approach": "behavioral_anomaly",
                    "metric": "members billed a genetic test",
                    "provider_value": int(n),
                    "robust_z": round(z, 3),
                    "review_reason": (
                        "Genetic-panel member count is high versus labs with the same specialty and type."
                    ),
                    **stats,
                    "peer_group": group,
                },
            )
        )
    return out
