"""Training labels, read from generator ground truth only.

Ground truth never enters a feature table. It is read here, joined to feature rows by
(provider, cutoff) or by case evidence, and kept in label columns that the feature guard bans.

Hazard event (30/60/90-day risk)
    For provider p and cutoff t: the first date after t on which p bills a planted fraudulent
    claim line (``is_fraud`` ground-truth rows; the line's service date). Monthly interval k
    covers (t + 30(k-1), t + 30k] days. Risk at 30/60/90 days is P(event in (t, t + h]).
    Hard negatives (``is_fraud=False``) never create events.

Case confirmation (P(confirm))
    A case built at cutoff t is confirmable when investigating it would find a planted scheme:
    one of its flagged lines is a planted fraudulent line; or one of its provider subjects
    billed planted fraudulent lines with service dates on or before t; or, for schemes planted
    as links rather than lines (rings, shells, referral monopolies, doctor shopping), a subject
    is a planted party. The subject rule matters because statistical alerts cite a capped
    sample of a provider's lines, which may not include the planted ones. Cases whose only
    planted evidence is a held-out scheme type are marked so training can exclude them.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import date, timedelta
from typing import Any

import pandas as pd

INTERVAL_DAYS = 30
HORIZONS = (30, 60, 90)
LINK_SCHEMES = frozenset({"G1", "G2", "G3", "S12", "S17"})


@dataclass(frozen=True)
class GroundTruthIndex:
    """Ground truth reshaped for labelling. Built once per synthetic world."""

    events: pd.DataFrame  # provider_id, event_date, scheme_id, held_out
    fraud_lines: dict[str, tuple[str, bool]]  # line_id -> (scheme_id, held_out)
    link_parties: dict[str, set[tuple[str, bool]]] = field(default_factory=dict)
    held_out_providers: frozenset[str] = frozenset()


def _as_list(value: Any) -> list[str]:
    if isinstance(value, (list, tuple)):
        return [str(v) for v in value]
    return []


def index_ground_truth(tables: dict[str, pd.DataFrame], ground_truth: pd.DataFrame) -> GroundTruthIndex:
    fraud = ground_truth[ground_truth["is_fraud"].astype(bool)] if not ground_truth.empty else ground_truth
    fraud_lines: dict[str, tuple[str, bool]] = {}
    link_parties: dict[str, set[tuple[str, bool]]] = {}
    for row in fraud.itertuples(index=False):
        held = bool(row.held_out)
        for lid in _as_list(row.line_ids):
            fraud_lines[lid] = (str(row.scheme_id), held)
        if str(row.scheme_id) in LINK_SCHEMES:
            parties = {str(row.provider_id)} if row.provider_id else set()
            parties |= {e for e in _as_list(row.entity_ids) if e.startswith("PRV")}
            for pid in parties:
                link_parties.setdefault(pid, set()).add((str(row.scheme_id), held))
    lines = tables["claim_line"][["line_id", "claim_id", "dos_from"]]
    lines = lines[lines["line_id"].astype(str).isin(fraud_lines)]
    billed = lines.merge(tables["claim"][["claim_id", "billing_provider_id"]], on="claim_id")
    events = pd.DataFrame(
        {
            "provider_id": billed["billing_provider_id"].astype(str),
            "event_date": pd.to_datetime(billed["dos_from"]).dt.date,
            "scheme_id": [fraud_lines[str(x)][0] for x in billed["line_id"]],
            "held_out": [fraud_lines[str(x)][1] for x in billed["line_id"]],
        }
    )
    held_providers = set(events.loc[events["held_out"], "provider_id"])
    held_providers |= {p for p, tags in link_parties.items() if any(h for _, h in tags)}
    return GroundTruthIndex(
        events=events.sort_values(["provider_id", "event_date"]).reset_index(drop=True),
        fraud_lines=fraud_lines,
        link_parties=link_parties,
        held_out_providers=frozenset(held_providers),
    )


def first_event_after(gt: GroundTruthIndex, cutoff: date, *, include_held_out: bool = False) -> dict[str, date]:
    """Earliest event strictly after the cutoff, per provider (held-out schemes excluded)."""
    later = gt.events[gt.events["event_date"] > cutoff]
    if not include_held_out:
        later = later[~later["held_out"]]
    if later.empty:
        return {}
    firsts = later.groupby("provider_id")["event_date"].min()
    return {str(pid): first for pid, first in firsts.items()}


def interval_of(event: date | None, cutoff: date) -> int | None:
    """1-based 30-day interval after the cutoff that contains the event (None if no event)."""
    if event is None:
        return None
    days = (event - cutoff).days
    if days <= 0:
        return None
    return (days - 1) // INTERVAL_DAYS + 1


def horizon_labels(event_interval: int | None, cutoff: date, data_end: date) -> dict[str, float | None]:
    """y_30/y_60/y_90: 1/0 when the window is fully observed, None when censored."""
    out: dict[str, float | None] = {}
    for h in HORIZONS:
        k = h // INTERVAL_DAYS
        if cutoff + timedelta(days=h) > data_end:
            out[f"y_{h}"] = None  # censored: scored only on fully observed windows
            continue
        out[f"y_{h}"] = 1.0 if event_interval is not None and event_interval <= k else 0.0
    return out


def case_confirm_label(case: dict[str, Any], gt: GroundTruthIndex, cutoff: date) -> tuple[int, bool]:
    """(label, held_out_only) for one case built at the cutoff."""
    tags: set[tuple[str, bool]] = set()
    for lid in case.get("line_ids") or []:
        hit = gt.fraud_lines.get(str(lid))
        if hit:
            tags.add(hit)
    subjects = {str(e) for e in case.get("entity_ids") or [case.get("primary_entity_id")] if e}
    for eid in subjects:
        tags |= gt.link_parties.get(eid, set())
    active = gt.events[gt.events["provider_id"].isin(subjects) & (gt.events["event_date"] <= cutoff)]
    tags |= set(zip(active["scheme_id"], active["held_out"].astype(bool), strict=True))
    if not tags:
        return 0, False
    held_only = all(held for _, held in tags)
    return 1, held_only
