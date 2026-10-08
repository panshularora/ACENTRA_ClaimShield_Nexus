from __future__ import annotations

from collections import defaultdict
from math import exp

import pandas as pd

from claimshield.core.ids import new_id
from claimshield.rules.engine import AlertDraft

STRONG_KINDS = frozenset(
    {
        "after_death",
        "excluded_party",
        "excluded_owner",
        "daily_minutes_cap",
        "ptp_pair",
        "unit_cap",
        "inpatient_overlap",
        "sex_implausible",
        "stay_compression",
        "identity_ring",
    }
)
MEDIUM_KINDS = frozenset(
    {
        "duplicate",
        "clone_billing",
        "ambulance_overlap",
        "doctor_shopping",
        "em_upcode_z",
        "hh_iqr",
        "genetic_mill",
        "referral_monopoly",
        "mileage_padding",
    }
)
# Beneficiary harm (CMS PIM scale, top = risk to a living member): a multi-prescriber opioid
# pattern, services billed during an inpatient stay, and impossible daily therapy hours.
HARM4_KINDS = frozenset({"doctor_shopping", "inpatient_overlap", "daily_minutes_cap"})
# An excluded provider or owner still treating members is a potential unsafe-provider signal.
HARM3_KINDS = frozenset({"excluded_party", "excluded_owner"})
# Program-integrity override: act now (stop payment exposure, refer), whatever the dollar rank.
# Services after death cannot harm that member, so they set priority, not harm.
PRIORITY_OVERRIDE_KINDS = frozenset({"after_death", "excluded_party", "excluded_owner"})
# Merge NPIs into one case only for a specific visible link. Statistical peers stay out.
LINK_KINDS = frozenset({"identity_ring", "excluded_owner", "referral_monopoly"})


def build_cases(
    alerts: list[AlertDraft],
    tables: dict[str, pd.DataFrame],
    communities: dict[str, str] | dict[str, int],
) -> list[dict]:
    _ = communities
    groups = _group_alerts(alerts)
    claims = tables["claim"]
    lines = tables["claim_line"]
    paid_by_line = lines.set_index("line_id")["paid"].to_dict()
    substantiated = _substantiated_providers(tables)
    cases = []
    for key, group in groups.items():
        entity_ids = _entity_ids_for(group)
        primary = group[0].entity_id
        line_ids = [lid for a in group for lid in a.line_ids]
        dollars = float(sum(paid_by_line.get(lid, 0.0) for lid in line_ids))
        members: set[str] = set()
        if line_ids:
            hit = lines[lines.line_id.isin(line_ids)].merge(
                claims[["claim_id", "member_id"]], on="claim_id"
            )
            members = set(hit["member_id"].astype(str).tolist())
        kinds = {str(a.evidence.get("kind")) for a in group}
        detectors = {a.detector for a in group}
        harm = _harm(kinds)
        override_kinds = sorted(kinds & PRIORITY_OVERRIDE_KINDS)
        severity = _severity(kinds)
        evidence = _evidence_strength(kinds, detectors, group)
        n_providers = max(1, len(entity_ids))
        hours = round(8.0 + 1.2 * (n_providers - 1) + 0.5 * len(kinds), 1)
        p_confirm = _confirmation_probability(
            evidence_strength=evidence,
            n_detectors=len(detectors),
            harm=harm,
            has_graph="graph" in detectors,
            prior=any(e in substantiated for e in entity_ids),
        )
        cases.append(
            {
                "case_id": new_id("CASE"),
                "primary_entity_id": primary,
                "primary_entity_type": "provider",
                "entity_ids": entity_ids,
                "alert_count": len(group),
                "line_ids": line_ids,
                "members_affected": len(members),
                "flagged_dollars": round(dollars, 2),
                "harm": harm,
                "priority_override": bool(override_kinds),
                "override_kinds": override_kinds,
                "severity": severity,
                "evidence_strength": round(evidence, 3),
                "estimated_hours": hours,
                "p_confirm": p_confirm,
                "lane": "open",
                "alerts": group,
                "group_key": key,
                "detectors": sorted(detectors),
                "kinds": sorted(kinds),
                "grouping": _grouping_for(group, entity_ids),
            }
        )
    return cases


def _group_alerts(alerts: list[AlertDraft]) -> dict[str, list[AlertDraft]]:
    parent: dict[str, str] = {}

    def find(x: str) -> str:
        parent.setdefault(x, x)
        while parent[x] != x:
            parent[x] = parent[parent[x]]
            x = parent[x]
        return x

    def union(a: str, b: str) -> None:
        ra, rb = find(a), find(b)
        if ra != rb:
            parent[rb] = ra

    keys_for: dict[int, list[str]] = {}
    for alert in alerts:
        ids = _link_ids(alert)
        for extra in ids[1:]:
            union(ids[0], extra)
        keys_for[id(alert)] = ids

    groups: dict[str, list[AlertDraft]] = defaultdict(list)
    for alert in alerts:
        ids = keys_for[id(alert)]
        root = find(ids[0]) if ids else f"ent:{alert.entity_id}"
        groups[root].append(alert)
    return groups


def _link_ids(alert: AlertDraft) -> list[str]:
    ids = [str(alert.entity_id)]
    kind = str(alert.evidence.get("kind") or "")
    if kind in LINK_KINDS:
        ids.extend(str(x) for x in alert.related_entity_ids if x)
    return [i for i in ids if i]


def _entity_ids_for(group: list[AlertDraft]) -> list[str]:
    seen: list[str] = []
    for alert in group:
        for eid in _link_ids(alert):
            if eid not in seen:
                seen.append(eid)
    return seen


def _grouping_for(group: list[AlertDraft], entity_ids: list[str]) -> dict:
    kinds = {str(a.evidence.get("kind") or "") for a in group}
    held_out: list[str] = []
    subjects = set(entity_ids)
    for alert in group:
        kind = str(alert.evidence.get("kind") or "")
        if kind in LINK_KINDS:
            continue
        for eid in alert.evidence.get("peer_ids") or []:
            sid = str(eid)
            if sid and sid not in subjects and sid not in held_out:
                held_out.append(sid)
    if "identity_ring" in kinds and len(entity_ids) > 1:
        rule = "identity_ring"
        text = (
            "These NPIs share owner, TIN, or contact links. They are one investigation. "
            "Providers used only as a like-with-like peer baseline are not parties to this case."
        )
    elif "excluded_owner" in kinds and len(entity_ids) > 1:
        rule = "excluded_owner"
        text = "These NPIs share an excluded owner. That ownership link is why they sit in one case."
    elif "referral_monopoly" in kinds and len(entity_ids) > 1:
        rule = "referral_link"
        text = "A concentrated referral link joins these NPIs. Peer specialty groups stay outside the case."
    else:
        rule = "same_provider"
        text = (
            "Alerts on this billing provider were grouped so the investigator reviews the pattern "
            "together. The portal is the queue; there is no separate notice per alert."
        )
    return {
        "rule": rule,
        "text": text,
        "entity_ids": entity_ids,
        "alert_count": len(group),
        "comparison_peers_held_out": held_out[:12],
    }


def _harm(kinds: set[str]) -> int:
    if kinds & HARM4_KINDS:
        return 4
    if kinds & HARM3_KINDS:
        return 3
    if kinds & STRONG_KINDS or kinds & MEDIUM_KINDS:
        return 2
    return 1


def _severity(kinds: set[str]) -> int:
    if "after_death" in kinds or "excluded_party" in kinds:
        return 4
    if kinds & STRONG_KINDS:
        return 3
    if kinds & MEDIUM_KINDS:
        return 2
    return 1


def _evidence_strength(kinds: set[str], detectors: set[str], group: list[AlertDraft]) -> float:
    if kinds & STRONG_KINDS:
        base = 0.62
    elif kinds & MEDIUM_KINDS:
        base = 0.50
    else:
        base = 0.28
    base += 0.08 * max(0, len(kinds) - 1)
    if "graph" in detectors and "rules" in detectors:
        base += 0.10
    if "anomaly" in detectors and len(detectors) > 1:
        base += 0.06
    mean_score = sum(a.score for a in group) / max(1, len(group))
    base = 0.7 * base + 0.3 * mean_score
    return min(0.95, base)


def _confirmation_probability(
    *,
    evidence_strength: float,
    n_detectors: int,
    harm: int,
    has_graph: bool,
    prior: bool,
) -> float:
    z = -2.0 + 2.4 * evidence_strength + 0.35 * min(3, n_detectors)
    if harm >= 4:
        z += 0.4
    if has_graph:
        z += 0.25
    if prior:
        z += 0.5
    return round(float(1.0 / (1.0 + exp(-z))), 3)


def _substantiated_providers(tables: dict[str, pd.DataFrame]) -> set[str]:
    inv = tables.get("investigation")
    subj = tables.get("investigation_subject")
    if inv is None or subj is None or inv.empty or subj.empty:
        return set()
    good = inv[inv["outcome"].isin(["substantiated", "referred", "education"])]
    if good.empty:
        return set()
    merged = subj.merge(good[["investigation_id"]], on="investigation_id")
    return set(merged["provider_id"].astype(str))
