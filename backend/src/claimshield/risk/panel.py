"""Build the training panel: many synthetic worlds, each scored at monthly cutoffs.

For every world (one generator seed) and cutoff t, the extract is cut back with ``as_of``,
the detectors run on that snapshot, and two row sets are produced:

* provider rows: provider features at t plus hazard labels from ground truth;
* case rows: features of the cases built at t plus the confirmation label.

Each row also carries the two baselines (old heuristic, rules-only) computed from the same
snapshot so the backtest compares like with like.
"""

from __future__ import annotations

import os
from concurrent.futures import ProcessPoolExecutor
from dataclasses import dataclass
from datetime import date, timedelta
from typing import Any

import pandas as pd

from claimshield.cases.builder import build_cases
from claimshield.pipeline.detectors import run_detectors
from claimshield.risk.features import case_features, provider_features
from claimshield.risk.heuristic import heuristic_hazard
from claimshield.risk.labels import (
    INTERVAL_DAYS,
    case_confirm_label,
    first_event_after,
    horizon_labels,
    index_ground_truth,
    interval_of,
)
from claimshield.risk.snapshot import as_of
from claimshield.rules.engine import AlertDraft
from claimshield.synth.generator import generate
from claimshield.synth.profiles import PROFILES

PANEL_START = date(2024, 1, 1)
FIRST_ORIGIN_MONTH = 3


@dataclass
class Panel:
    providers: pd.DataFrame
    cases: pd.DataFrame


def origin_date(month: int) -> date:
    return PANEL_START + timedelta(days=INTERVAL_DAYS * month)


def world_end(profile: str) -> date:
    return origin_date(PROFILES[profile].n_months)


def origin_months(profile: str) -> list[int]:
    return list(range(FIRST_ORIGIN_MONTH, PROFILES[profile].n_months))


def build_world(profile: str, seed: int) -> Panel:
    ds = generate(profile=profile, seed=seed)
    gt = index_ground_truth(ds.tables, ds.ground_truth)
    end = world_end(profile)
    provider_frames: list[pd.DataFrame] = []
    case_frames: list[pd.DataFrame] = []
    for month in origin_months(profile):
        cutoff = origin_date(month)
        snap = as_of(ds.tables, cutoff)
        det = run_detectors(snap)
        feats = provider_features(snap, det.alerts, det.graph, det.strong, cutoff)
        cases = build_cases(det.alerts, snap, det.strong)

        first = first_event_after(gt, cutoff)
        first_any = first_event_after(gt, cutoff, include_held_out=True)
        rows = feats.reset_index()
        rows["world"] = seed
        rows["origin_month"] = month
        rows["event_interval"] = [interval_of(first.get(p), cutoff) for p in rows["provider_id"]]
        any_interval = [interval_of(first_any.get(p), cutoff) for p in rows["provider_id"]]
        labels = pd.DataFrame([horizon_labels(i, cutoff, end) for i in rows["event_interval"]])
        held = pd.DataFrame([horizon_labels(i, cutoff, end) for i in any_interval]).add_prefix("all_")
        rows = pd.concat([rows, labels, held], axis=1)
        rows["censor_interval"] = min(3, max(0, (end - cutoff).days // INTERVAL_DAYS))
        rows["held_out_provider"] = rows["provider_id"].isin(gt.held_out_providers)
        rows["rules_only"] = [_rules_count(det.alerts, p) for p in rows["provider_id"]]
        rows["heuristic_f30"], rows["heuristic_f60"], rows["heuristic_f90"] = zip(
            *[_heuristic_provider(cases, p) for p in rows["provider_id"]], strict=True
        )
        provider_frames.append(rows)

        if cases:
            cf = case_features(cases)
            labels_c = [case_confirm_label(c, gt, cutoff) for c in cases]
            cf["world"] = seed
            cf["origin_month"] = month
            cf["y_confirm"] = [lab for lab, _ in labels_c]
            cf["held_out_case"] = [held_only for _, held_only in labels_c]
            cf["hours"] = [float(c["estimated_hours"]) for c in cases]
            cf["heuristic_p"] = [float(c["p_confirm"]) for c in cases]
            cf["rules_only"] = [_case_rules_score(c) for c in cases]
            case_frames.append(cf)
    providers = pd.concat(provider_frames, ignore_index=True)
    cases_df = pd.concat(case_frames, ignore_index=True) if case_frames else pd.DataFrame()
    return Panel(providers=providers, cases=cases_df)


def build_panel(profile: str, seeds: list[int], *, workers: int | None = None) -> Panel:
    n = workers if workers is not None else min(len(seeds), os.cpu_count() or 1)
    if n <= 1:
        worlds = [build_world(profile, s) for s in seeds]
    else:
        with ProcessPoolExecutor(max_workers=n) as pool:
            worlds = list(pool.map(build_world, [profile] * len(seeds), seeds))
    return Panel(
        providers=pd.concat([w.providers for w in worlds], ignore_index=True),
        cases=pd.concat([w.cases for w in worlds], ignore_index=True),
    )


def _rules_count(alerts: list[AlertDraft], provider_id: str) -> float:
    return float(
        sum(1 for a in alerts if a.detector == "rules" and provider_id in {a.entity_id, *a.related_entity_ids})
    )


def _case_rules_score(case: dict[str, Any]) -> float:
    rule_alerts = [a for a in case["alerts"] if a.detector == "rules"]
    kinds = {a.evidence.get("kind") for a in rule_alerts}
    top = max((float(a.score) for a in rule_alerts), default=0.0)
    return float(len(kinds)) + 0.01 * top


def _heuristic_provider(cases: list[dict[str, Any]], provider_id: str) -> tuple[float, float, float]:
    """Old formula as a provider score: worst case containing the provider, else p=0, harm=0."""
    best = heuristic_hazard(0.0, 0)
    for case in cases:
        if provider_id in (case.get("entity_ids") or [case["primary_entity_id"]]):
            cand = heuristic_hazard(float(case["p_confirm"]), int(case["harm"]))
            if cand[3] > best[3]:
                best = cand
    return best[1], best[2], best[3]
