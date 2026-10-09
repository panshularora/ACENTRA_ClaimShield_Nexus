"""How a case was built and which extract tables support each finding."""

from __future__ import annotations

from typing import Any

from claimshield.cases.builder import HARM4_KINDS, LINK_KINDS, PRIORITY_OVERRIDE_KINDS
from claimshield.db.models import Alert, Batch, Case, PipelineRun
from claimshield.rules.catalog import rule_title as catalog_title

TABLE_ROLES: dict[str, str] = {
    "claim": "Paid claim header (who billed, which member, when it was paid)",
    "claim_line": "Each service on a paid claim (code, units, dollars, date)",
    "member": "Member file (including date of death when it is on record)",
    "provider": "Provider enrollment (specialty, type, location)",
    "eligibility_span": "Coverage dates",
    "evv_visit": "Home-visit check-in records",
    "inpatient_stay": "Hospital admit and discharge dates",
    "rx_fill": "Pharmacy fills",
    "exclusion_record": "Exclusion list (matched on NPI and name)",
    "referral": "Who referred whom",
    "ownership_link": "Who owns which NPI",
    "owner": "Owner names on file",
    "contact_point": "Shared phone, email, or bank details",
    "location": "Practice address",
    "investigation": "Earlier SIU outcomes on this provider",
}

KIND_TABLES: dict[str, tuple[str, ...]] = {
    "after_death": ("claim", "claim_line", "member"),
    "excluded_party": ("claim", "claim_line", "exclusion_record", "provider"),
    "excluded_owner": ("ownership_link", "owner", "exclusion_record", "provider", "claim_line"),
    "daily_minutes_cap": ("claim", "claim_line"),
    "ptp_pair": ("claim", "claim_line"),
    "unit_cap": ("claim", "claim_line"),
    "inpatient_overlap": ("claim", "claim_line", "inpatient_stay"),
    "sex_implausible": ("claim", "claim_line", "member"),
    "stay_compression": ("claim", "claim_line", "inpatient_stay"),
    "identity_ring": ("provider", "ownership_link", "contact_point", "claim", "claim_line"),
    "duplicate": ("claim", "claim_line"),
    "clone_billing": ("claim", "claim_line"),
    "ambulance_overlap": ("claim", "claim_line"),
    "doctor_shopping": ("claim", "claim_line", "rx_fill"),
    "em_upcode_z": ("claim", "claim_line", "provider"),
    "hh_iqr": ("claim", "claim_line", "provider", "evv_visit"),
    "genetic_mill": ("claim", "claim_line", "provider"),
    "referral_monopoly": ("referral", "claim", "claim_line", "provider"),
    "mileage_padding": ("claim", "claim_line"),
    "evv_missing": ("claim", "claim_line", "evv_visit"),
}

DETECTOR_METHOD: dict[str, str] = {
    "rules": "A check on paid claim lines. It flags a pattern for a person to review.",
    "anomaly": (
        "This provider looks different from similar ones (same specialty and setting). "
        "That is a reason to look at the claims, not a conclusion."
    ),
    "graph": "This provider is linked to others by ownership, shared contact, or referrals.",
}

APPROACH_BY_DETECTOR = {
    "rules": "hard_rule",
    "anomaly": "behavioral_anomaly",
    "graph": "network_graph",
}


def grouping_from_alerts(alerts: list[Alert], entity_ids: list[str]) -> dict[str, Any]:
    kinds = {str((a.evidence or {}).get("kind") or "") for a in alerts}
    subjects = set(entity_ids)
    held_out: list[str] = []
    for alert in alerts:
        kind = str((alert.evidence or {}).get("kind") or "")
        if kind in LINK_KINDS:
            continue
        for eid in (alert.evidence or {}).get("peer_ids") or []:
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
        "alert_count": len(alerts),
        "comparison_peers_held_out": held_out[:12],
    }


def urgent_alerts(alerts: list[Alert]) -> list[dict[str, Any]]:
    out: list[dict[str, Any]] = []
    for alert in alerts:
        kind = str((alert.evidence or {}).get("kind") or "")
        if kind not in HARM4_KINDS | PRIORITY_OVERRIDE_KINDS:
            continue
        out.append(
            {
                "alert_id": alert.alert_id,
                "rule_id": alert.rule_id,
                "kind": kind,
                "label": kind.replace("_", " "),
                "entity_id": alert.entity_id,
                "line_ids": alert.line_ids or [],
            }
        )
    return out


def tables_for_kind(kind: str, detector: str) -> list[dict[str, str]]:
    names = KIND_TABLES.get(kind) or ("claim", "claim_line")
    if detector == "anomaly" and "provider" not in names:
        names = (*names, "provider")
    return [{"table": name, "role": TABLE_ROLES.get(name, name)} for name in names]


def alert_lineage(alert: Alert) -> dict[str, Any]:
    evidence = alert.evidence or {}
    kind = str(evidence.get("kind") or "")
    how = evidence.get("review_reason") or catalog_title(alert.rule_id, "")
    fields = [
        key
        for key in (
            "code",
            "dos",
            "member_id",
            "n_peers",
            "peer_median",
            "robust_z",
            "edge_kinds",
            "owner_id",
        )
        if key in evidence
    ]
    return {
        "detector": alert.detector,
        "approach": evidence.get("approach") or APPROACH_BY_DETECTOR.get(alert.detector, alert.detector),
        "method": DETECTOR_METHOD.get(alert.detector, alert.detector),
        "kind": kind,
        "how": how,
        "tables": tables_for_kind(kind, alert.detector),
        "fields_used": fields,
        "line_ids": alert.line_ids or [],
        "comparison_peers_held_out": (
            [] if kind in LINK_KINDS else [str(x) for x in (evidence.get("peer_ids") or [])][:8]
        ),
    }


def case_provenance(
    *,
    case: Case,
    alerts: list[Alert],
    run: PipelineRun | None,
    batch: Batch | None,
    grouping: dict[str, Any],
    why_rank_text: str,
) -> dict[str, Any]:
    extract = "synthetic generator"
    if batch is not None:
        if batch.adapter == "s3_csv":
            source = (batch.load_report or {}).get("source") or {}
            extract = f"S3 extract {source.get('key') or source.get('prefix') or ''}".strip()
        elif batch.adapter == "synthetic":
            extract = f"synthetic extract profile={batch.profile} seed={batch.seed}"
        else:
            extract = batch.adapter
    by_detector: dict[str, int] = {}
    for alert in alerts:
        by_detector[alert.detector] = by_detector.get(alert.detector, 0) + 1
    tables: dict[str, dict[str, str]] = {}
    for alert in alerts:
        kind = str((alert.evidence or {}).get("kind") or "")
        for item in tables_for_kind(kind, alert.detector):
            tables[item["table"]] = item
    steps = [
        {
            "step": 1,
            "name": "Paid claims",
            "detail": f"Loaded {extract}.",
        },
        {
            "step": 2,
            "name": "Claim checks",
            "detail": f"{by_detector.get('rules', 0)} claim-line check(s) flagged a pattern.",
        },
        {
            "step": 3,
            "name": "Similar providers",
            "detail": (
                f"{by_detector.get('anomaly', 0)} comparison(s) with similar providers. "
                "Those providers are a baseline, not parties to this case."
            ),
        },
        {
            "step": 4,
            "name": "Linked providers",
            "detail": (f"{by_detector.get('graph', 0)} link(s) by ownership, shared contact, or referrals."),
        },
        {
            "step": 5,
            "name": "Case file",
            "detail": grouping["text"],
        },
        {
            "step": 6,
            "name": "Rank",
            "detail": why_rank_text
            or "Combined rank of scheme severity, financial exposure, member impact, evidence, and urgency.",
        },
    ]
    if run is not None:
        steps[0]["detail"] += f" Run {run.run_id}."
    return {
        "extract": extract,
        "steps": steps,
        "data_sources": list(tables.values()),
        "grouping": grouping,
        "urgent": urgent_alerts(alerts),
        "suspicion_only": True,
    }
