"""As-of features for the risk models.

Provider features feed the 30/60/90 hazard; case features feed P(confirm). Both are computed
from a snapshot (``snapshot.as_of``) and the detector alerts run on that snapshot, so nothing
after the cutoff can reach a feature. ``assert_clean`` is the guard for leakage traps 4 and 6:
it rejects ground-truth, process and identifier columns by name.
"""

from __future__ import annotations

import math
import re
from collections import defaultdict
from collections.abc import Iterable
from datetime import date, timedelta
from typing import Any

import networkx as nx
import numpy as np
import pandas as pd

from claimshield.anomaly.peer import robust_z
from claimshield.graph.build import STRONG_EDGE_KINDS
from claimshield.rules.engine import AlertDraft

# Alert kinds the detectors can emit today. Unknown kinds still count in the totals.
ALERT_KINDS: tuple[str, ...] = (
    "after_death",
    "ambulance_overlap",
    "clone_billing",
    "daily_minutes_cap",
    "doctor_shopping",
    "duplicate",
    "em_upcode_z",
    "evv_missing",
    "excluded_owner",
    "excluded_party",
    "genetic_mill",
    "hh_iqr",
    "identity_ring",
    "inpatient_overlap",
    "mileage_padding",
    "pos_mismatch",
    "ptp_pair",
    "referral_monopoly",
    "sex_implausible",
    "stay_compression",
    "unit_cap",
)
DETECTORS: tuple[str, ...] = ("rules", "anomaly", "graph")

PROVIDER_FEATURES: tuple[str, ...] = (
    "alerts_rules",
    "alerts_anomaly",
    "alerts_graph",
    "alert_kinds",
    "alert_max_score",
    "alerts_recent_30",
    "alerts_recent_90",
    "days_since_alert_line",
    "lines_30",
    "lines_90",
    "paid_90",
    "members_90",
    "lines_trend",
    "active_30",
    "paid_per_member_z",
    "graph_strong_degree",
    "graph_location_degree",
    "graph_referral_degree",
    "ring_size",
    "referrals_in_90",
    *(f"kind_{k}" for k in ALERT_KINDS),
)

CASE_FEATURES: tuple[str, ...] = (
    "n_alerts",
    "n_kinds",
    "n_detectors",
    "has_rules",
    "has_anomaly",
    "has_graph",
    "max_score",
    "mean_score",
    "n_lines",
    "flagged_dollars",
    "members",
    "n_entities",
    *(f"kind_{k}" for k in ALERT_KINDS),
)

FEATURE_LABELS: dict[str, str] = {
    "alerts_rules": "Rule hits to date",
    "alerts_anomaly": "Peer-anomaly hits to date",
    "alerts_graph": "Network hits to date",
    "alert_kinds": "Distinct signal types",
    "alert_max_score": "Strongest alert score",
    "alerts_recent_30": "Alerts on lines in the last 30 days",
    "alerts_recent_90": "Alerts on lines in the last 90 days",
    "days_since_alert_line": "Time since the last flagged line",
    "lines_30": "Claim lines, last 30 days",
    "lines_90": "Claim lines, last 90 days",
    "paid_90": "Paid dollars, last 90 days",
    "members_90": "Distinct members, last 90 days",
    "lines_trend": "Billing trend (last 30 vs prior 60 days)",
    "active_30": "Billed in the last 30 days",
    "paid_per_member_z": "Paid per member vs service-line peers (robust z)",
    "graph_strong_degree": "Owner/TIN/contact links to other NPIs",
    "graph_location_degree": "NPIs at the same address",
    "graph_referral_degree": "Referral partners",
    "ring_size": "Size of the owner/TIN/contact cluster",
    "referrals_in_90": "Referrals received, last 90 days",
    "n_alerts": "Alerts in the case",
    "n_kinds": "Distinct signal types",
    "n_detectors": "Independent detector layers",
    "has_rules": "Rule layer fired",
    "has_anomaly": "Peer-anomaly layer fired",
    "has_graph": "Network layer fired",
    "max_score": "Strongest alert score",
    "mean_score": "Mean alert score",
    "n_lines": "Flagged claim lines",
    "flagged_dollars": "Flagged paid dollars",
    "members": "Members on flagged lines",
    "n_entities": "Linked NPIs in the case",
    "interval_2": "Second 30-day interval",
    "interval_3": "Third 30-day interval",
    **{f"kind_{k}": f"Signal: {k.replace('_', ' ')}" for k in ALERT_KINDS},
}

# Names that must never be features: ground truth, investigation process/outcomes, queue state,
# identifiers, and generator artefacts (round amounts, claim lags, enrolment tenure).
BANNED_FEATURE_PATTERN = re.compile(
    r"scheme|ground_truth|is_fraud|held_out|variant|label|^y_|event|"
    r"investigation|outcome|substantiat|referred|suspen|records_request|decision|"
    r"(^|_)(lane|assignee|override|sla|status)(_|$)|p_confirm|"
    r"(^|_)ids?(_|$)|npi|tin_token|(^|_)name(_|$)|"
    r"round|cents|(^|_)lag(_|$)|received|adjudicat|enroll|tenure|first_seen",
)


LOG_SCALED = frozenset(
    {
        "alerts_rules",
        "alerts_anomaly",
        "alerts_graph",
        "alerts_recent_30",
        "alerts_recent_90",
        "lines_30",
        "lines_90",
        "paid_90",
        "members_90",
        "graph_strong_degree",
        "graph_location_degree",
        "graph_referral_degree",
        "referrals_in_90",
        "n_alerts",
        "n_lines",
        "flagged_dollars",
        "members",
    }
)


def display_value(feature: str, value: float) -> float:
    """Undo model-side scaling so the API shows counts, dollars and days."""
    if feature in LOG_SCALED:
        return round(math.expm1(value), 2)
    if feature == "days_since_alert_line":
        return round(value * 365.0)
    return round(float(value), 3)


def assert_clean(columns: Iterable[str]) -> None:
    bad = [c for c in columns if BANNED_FEATURE_PATTERN.search(c)]
    if bad:
        raise ValueError(f"banned feature columns: {bad}")


def _log1p(x: float) -> float:
    return math.log1p(max(0.0, float(x)))


def _alert_providers(alert: AlertDraft) -> list[str]:
    ids = [str(alert.entity_id), *(str(x) for x in alert.related_entity_ids)]
    return [i for i in dict.fromkeys(ids) if i]


def provider_features(
    tables: dict[str, pd.DataFrame],
    alerts: list[AlertDraft],
    graph: nx.Graph,
    strong: dict[str, str],
    cutoff: date,
) -> pd.DataFrame:
    """One row per enrolled provider in the snapshot, indexed by provider_id."""
    providers = tables["provider"][["provider_id", "service_line"]].copy()
    providers["provider_id"] = providers["provider_id"].astype(str)
    pids = providers["provider_id"].tolist()
    feats: dict[str, dict[str, float]] = {
        pid: dict.fromkeys(PROVIDER_FEATURES, 0.0) for pid in pids
    }

    lines = tables["claim_line"][["line_id", "claim_id", "dos_from", "paid"]].merge(
        tables["claim"][["claim_id", "billing_provider_id", "member_id"]], on="claim_id"
    )
    lines["dos"] = pd.to_datetime(lines["dos_from"])
    lines["billing_provider_id"] = lines["billing_provider_id"].astype(str)
    ts = pd.Timestamp(cutoff)
    dos_by_line = dict(zip(lines["line_id"].astype(str), lines["dos"], strict=False))

    last_30 = lines[lines["dos"] > ts - timedelta(days=30)]
    last_90 = lines[lines["dos"] > ts - timedelta(days=90)]
    prior_60 = lines[
        (lines["dos"] > ts - timedelta(days=90)) & (lines["dos"] <= ts - timedelta(days=30))
    ]
    n30 = last_30.groupby("billing_provider_id").size()
    n90 = last_90.groupby("billing_provider_id").size()
    np60 = prior_60.groupby("billing_provider_id").size()
    paid90 = last_90.groupby("billing_provider_id")["paid"].sum()
    mem90 = last_90.groupby("billing_provider_id")["member_id"].nunique()
    for pid in pids:
        f = feats[pid]
        a, b = float(n30.get(pid, 0)), float(np60.get(pid, 0))
        f["lines_30"] = _log1p(a)
        f["lines_90"] = _log1p(n90.get(pid, 0))
        f["paid_90"] = _log1p(paid90.get(pid, 0.0))
        f["members_90"] = _log1p(mem90.get(pid, 0))
        f["lines_trend"] = math.log((a + 1.0) / (b / 2.0 + 1.0))
        f["active_30"] = 1.0 if a > 0 else 0.0

    per_member = (paid90 / mem90.clip(lower=1)).rename("ppm")
    lines_by_service = providers.set_index("provider_id")["service_line"]
    for _, group in lines_by_service.groupby(lines_by_service):
        members = [p for p in group.index if p in per_member.index]
        values = np.array([float(per_member[p]) for p in members], dtype=float)
        for p in members:
            z = robust_z(float(per_member[p]), values) if values.size >= 5 else 0.0
            feats[p]["paid_per_member_z"] = float(np.clip(z, -5.0, 10.0))

    kinds_for: dict[str, set[str]] = defaultdict(set)
    last_line: dict[str, pd.Timestamp] = {}
    for alert in alerts:
        kind = str(alert.evidence.get("kind") or "")
        line_dates = [dos_by_line[lid] for lid in alert.line_ids if lid in dos_by_line]
        newest = max(line_dates) if line_dates else None
        for pid in _alert_providers(alert):
            if pid not in feats:
                continue
            f = feats[pid]
            if alert.detector in DETECTORS:
                f[f"alerts_{alert.detector}"] += 1.0
            f["alert_max_score"] = max(f["alert_max_score"], float(alert.score))
            kinds_for[pid].add(kind)
            if f"kind_{kind}" in f:
                f[f"kind_{kind}"] = 1.0
            if newest is not None:
                if newest > ts - timedelta(days=30):
                    f["alerts_recent_30"] += 1.0
                if newest > ts - timedelta(days=90):
                    f["alerts_recent_90"] += 1.0
                if pid not in last_line or newest > last_line[pid]:
                    last_line[pid] = newest
    for pid in pids:
        f = feats[pid]
        for det in DETECTORS:
            f[f"alerts_{det}"] = _log1p(f[f"alerts_{det}"])
        f["alerts_recent_30"] = _log1p(f["alerts_recent_30"])
        f["alerts_recent_90"] = _log1p(f["alerts_recent_90"])
        f["alert_kinds"] = float(len(kinds_for.get(pid, ())))
        gap = (ts - last_line[pid]).days if pid in last_line else 365
        f["days_since_alert_line"] = min(365.0, float(gap)) / 365.0

    ring_sizes: dict[str, int] = defaultdict(int)
    for rid in strong.values():
        ring_sizes[rid] += 1
    for pid in pids:
        if not graph.has_node(pid):
            continue
        strong_n = loc_n = ref_n = 0
        for _, _other, data in graph.edges(pid, data=True):
            kinds = data.get("kinds") or {data.get("kind")}
            if kinds & STRONG_EDGE_KINDS:
                strong_n += 1
            if "shared_location" in kinds:
                loc_n += 1
            if "referral" in kinds:
                ref_n += 1
        f = feats[pid]
        f["graph_strong_degree"] = _log1p(strong_n)
        f["graph_location_degree"] = _log1p(loc_n)
        f["graph_referral_degree"] = _log1p(ref_n)
        f["ring_size"] = float(ring_sizes.get(strong.get(pid, ""), 0))

    refs = tables.get("referral")
    if refs is not None and not refs.empty:
        recent = refs[pd.to_datetime(refs["date"]) > ts - timedelta(days=90)]
        received = recent.groupby(recent["receiving_id"].astype(str)).size()
        for pid, n in received.items():
            if pid in feats:
                feats[pid]["referrals_in_90"] = _log1p(n)

    frame = pd.DataFrame.from_dict(feats, orient="index", columns=list(PROVIDER_FEATURES))
    frame.index.name = "provider_id"
    assert_clean(frame.columns)
    return frame.astype(float)


def case_feature_row(case: dict[str, Any]) -> dict[str, float]:
    alerts: list[AlertDraft] = list(case.get("alerts") or [])
    scores = [float(a.score) for a in alerts] or [0.0]
    kinds = {str(a.evidence.get("kind") or "") for a in alerts}
    detectors = {a.detector for a in alerts}
    row = dict.fromkeys(CASE_FEATURES, 0.0)
    row.update(
        {
            "n_alerts": _log1p(len(alerts)),
            "n_kinds": float(len(kinds)),
            "n_detectors": float(len(detectors)),
            "has_rules": float("rules" in detectors),
            "has_anomaly": float("anomaly" in detectors),
            "has_graph": float("graph" in detectors),
            "max_score": max(scores),
            "mean_score": float(np.mean(scores)),
            "n_lines": _log1p(len(case.get("line_ids") or [])),
            "flagged_dollars": _log1p(case.get("flagged_dollars") or 0.0),
            "members": _log1p(case.get("members_affected") or 0),
            "n_entities": float(len(case.get("entity_ids") or [])),
        }
    )
    for kind in kinds:
        if f"kind_{kind}" in row:
            row[f"kind_{kind}"] = 1.0
    return row


def case_features(cases: list[dict[str, Any]]) -> pd.DataFrame:
    frame = pd.DataFrame([case_feature_row(c) for c in cases], columns=list(CASE_FEATURES))
    assert_clean(frame.columns)
    return frame.astype(float)
