"""Shared case helpers: labels, alert serialisation, member masking and unmask audit."""

from __future__ import annotations

from datetime import date, datetime
from typing import Any

from sqlalchemy import select
from sqlalchemy.orm import Session

from claimshield.audit.service import append_event
from claimshield.auth.rbac import has_permission
from claimshield.cases.provenance import APPROACH_BY_DETECTOR, alert_lineage
from claimshield.core.clock import canonical_iso
from claimshield.core.errors import NotFound
from claimshield.db.models import Alert, Case, Claim, ClaimLine, Member, User
from claimshield.rules.catalog import rule_title as catalog_title

RULE_TITLES = {
    "R-DUP-001": "Same member, provider, code, date of service",
    "R-PTP-001": "Procedure-to-procedure unbundling (indicator 0)",
    "R-UNIT-001": "Units above synthetic MUE cap",
    "R-DEATH-001": "Date of service after date of death",
    "R-BH-001": "More than 960 billed minutes on one clinician-day",
    "R-IP-001": "Outpatient/ABA service during an inpatient stay",
    "R-EVV-001": "Home-health visit with no EVV row",
    "R-LEIE-001": "Provider matches synthetic LEIE (NPI and name agree, DOS after exclusion)",
    "R-RX-001": "Multiple-prescriber / multiple-pharmacy opioid pattern (member-level)",
    "R-SEX-001": "Sex-procedure coding conflict (data-quality check; KX/CC45 excluded)",
    "R-POS-001": "Office E/M billed at inpatient or ambulance POS",
    "R-AMB-001": "Several long recorded ambulance trips on one crew-day (overlap not tested)",
    "R-CLONE-001": "Same-day volume of one service across many members far above peers",
    "R-STAY-001": "High-DRG facility claim with same-day admit and discharge",
    "R-MILE-001": "Urban ambulance mileage above plausible cap",
    "G-RING-001": "Shared owner, TIN, or bank across multiple NPIs",
    "G-REF-001": "Referral volume concentrated on one receiver",
    "G-OWN-001": "Owner matches synthetic LEIE record (name, DOB and address agree)",
    "A-EM-001": "E/M mix vs peers",
    "A-HH-001": "Home-health volume fence",
    "A-GEN-001": "Genetic-testing mill",
}
KIND_LABELS = {
    "duplicate": "Duplicate billing",
    "ptp_pair": "Unbundling (PTP)",
    "unit_cap": "Units over cap",
    "after_death": "Service after death",
    "daily_minutes_cap": "Impossible daily hours",
    "inpatient_overlap": "Billed during inpatient stay",
    "evv_missing": "Home visit without EVV",
    "excluded_party": "Excluded-party NPI",
    "doctor_shopping": "Multiple-prescriber opioid pattern (member)",
    "sex_implausible": "Sex-procedure coding conflict",
    "pos_mismatch": "Place-of-service mismatch",
    "ambulance_overlap": "Long ambulance trips, one crew-day",
    "clone_billing": "Same-day volume far above peers",
    "stay_compression": "Same-day high-DRG stay",
    "mileage_padding": "Urban ambulance mileage padding",
    "identity_ring": "Shared identity across NPIs",
    "referral_monopoly": "Concentrated referral volume",
    "excluded_owner": "Excluded owner",
    "em_upcode_z": "E/M mix vs peers",
    "hh_iqr": "Home-health volume fence",
    "genetic_mill": "Genetic-testing mill",
}


def iso(value: Any) -> str | None:
    if value is None:
        return None
    if isinstance(value, datetime):
        return canonical_iso(value) if value.tzinfo else value.date().isoformat()
    if isinstance(value, date):
        return value.isoformat()
    return str(value)


def get_case_or_404(session: Session, case_id: str) -> Case:
    case = session.get(Case, case_id)
    if case is None:
        raise NotFound("case not found")
    return case


def alerts_for(session: Session, case_id: str) -> list[Alert]:
    return list(session.execute(select(Alert).where(Alert.case_id == case_id)).scalars().all())


def line_ids_for(alerts: list[Alert]) -> list[str]:
    seen: list[str] = []
    for alert in alerts:
        for lid in alert.line_ids or []:
            if lid not in seen:
                seen.append(lid)
    return seen


def member_display(member_id: str, unmask: bool, name: str | None) -> dict[str, Any]:
    tail = member_id[-4:] if member_id else "????"
    if unmask and name:
        return {"member_id": member_id, "name": name, "display": name, "masked": False}
    return {
        "member_id": member_id,
        "name": None,
        "display": f"Member ·{tail}",
        "masked": True,
    }


def can_unmask(user: User) -> bool:
    return has_permission(user.role, "member:unmask") or has_permission(user.role, "admin:*")


def serialize_alert(alert: Alert) -> dict[str, Any]:
    kind = str((alert.evidence or {}).get("kind") or "")
    evidence = alert.evidence or {}
    approach = str(evidence.get("approach") or APPROACH_BY_DETECTOR.get(alert.detector, alert.detector))
    return {
        "alert_id": alert.alert_id,
        "detector": alert.detector,
        "approach": approach,
        "rule_id": alert.rule_id,
        "rule_version": alert.rule_version,
        "rule_title": catalog_title(alert.rule_id, RULE_TITLES.get(alert.rule_id or "", alert.rule_id)),
        "policy_ref": evidence.get("policy_ref"),
        "entity_id": alert.entity_id,
        "entity_type": alert.entity_type,
        "score": alert.score,
        "evidence": evidence,
        "line_ids": alert.line_ids or [],
        "kind": kind,
        "label": KIND_LABELS.get(kind, kind.replace("_", " ") if kind else "Signal"),
        "review_reason": evidence.get("review_reason")
        or catalog_title(
            alert.rule_id, RULE_TITLES.get(alert.rule_id or "", "Review the supporting claims and fields.")
        ),
        "lineage": alert_lineage(alert),
    }


def audit_unmask(
    session: Session,
    *,
    user: User,
    case: Case,
    surface: str,
    unmask: bool,
) -> bool:
    reveal = unmask and can_unmask(user)
    if reveal:
        append_event(
            session,
            actor_id=user.id,
            role=user.role,
            action="member.unmask",
            object_type="case",
            object_id=case.case_id,
            payload={"surface": surface, "minimum_necessary": True},
        )
    return reveal


def claim_rows(session: Session, alerts: list[Alert], *, reveal: bool) -> list[dict[str, Any]]:
    """Flagged claim lines for a set of alerts, with masked or revealed member display."""
    lids = line_ids_for(alerts)
    if not lids:
        return []

    lines = list(session.execute(select(ClaimLine).where(ClaimLine.line_id.in_(lids))).scalars().all())
    by_line: dict[str, list[dict[str, Any]]] = {}
    for alert in alerts:
        payload = serialize_alert(alert)
        for lid in alert.line_ids or []:
            by_line.setdefault(lid, []).append(
                {"alert_id": payload["alert_id"], "rule_id": payload["rule_id"], "label": payload["label"]}
            )
    return serialize_lines(session, lines, reveal=reveal, signals=by_line)


def serialize_lines(
    session: Session,
    lines: list[ClaimLine],
    *,
    reveal: bool,
    signals: dict[str, list[dict[str, Any]]] | None = None,
) -> list[dict[str, Any]]:
    """Claim-line rows (ClaimRow shape) sorted by date of service, members masked unless revealed."""
    by_line = signals or {}
    claim_ids = {ln.claim_id for ln in lines}
    claims = {
        c.claim_id: c for c in session.execute(select(Claim).where(Claim.claim_id.in_(claim_ids))).scalars().all()
    }
    member_ids = {c.member_id for c in claims.values()}
    members = {
        m.member_id: m for m in session.execute(select(Member).where(Member.member_id.in_(member_ids))).scalars().all()
    }
    rows = []
    for ln in lines:
        claim = claims.get(ln.claim_id)
        member = members.get(claim.member_id) if claim else None
        member_id = claim.member_id if claim else ""
        rows.append(
            {
                "line_id": ln.line_id,
                "claim_id": ln.claim_id,
                "dos_from": iso(ln.dos_from),
                "dos_to": iso(ln.dos_to),
                "code": ln.code,
                "code_system": ln.code_system,
                "modifiers": ln.modifiers or [],
                "units": ln.units,
                "minutes": ln.minutes,
                "pos": ln.pos,
                "charge": ln.charge,
                "allowed": ln.allowed,
                "paid": ln.paid,
                "rendering_provider_id": ln.rendering_provider_id,
                "ordering_provider_id": ln.ordering_provider_id,
                "billing_provider_id": claim.billing_provider_id if claim else None,
                "facility_id": claim.facility_id if claim else None,
                "claim_type": claim.claim_type if claim else None,
                "claim_status": claim.status if claim else None,
                "received_date": iso(claim.received_date) if claim else None,
                "adjudicated_date": iso(claim.adjudicated_date) if claim else None,
                "member": member_display(member_id, reveal, member.name if member else None),
                "signals": by_line.get(ln.line_id, []),
                "source_system": claim.source_system if claim else None,
                "source_ref": claim.source_ref if claim else None,
            }
        )
    rows.sort(key=lambda r: (r["dos_from"] or "", r["line_id"]))
    return rows
