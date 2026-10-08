"""Case investigation pack: claims, template brief, timeline, 2-hop network, decisions."""

from __future__ import annotations

from datetime import date, datetime
from typing import Any

from sqlalchemy import select
from sqlalchemy.orm import Session

from claimshield.audit.service import append_event, chain_status
from claimshield.auth.rbac import has_permission
from claimshield.core.clock import canonical_iso
from claimshield.core.errors import NotFound, ValidationFailed
from claimshield.core.ids import new_id
from claimshield.db.models import (
    Alert,
    Case,
    Claim,
    ClaimLine,
    Decision,
    Facility,
    InpatientStay,
    Investigation,
    InvestigationSubject,
    Member,
    Owner,
    OwnershipLink,
    Provider,
    Referral,
    User,
    WikiPage,
)

ACTIONS = ("escalate", "monitor", "dismiss", "needs_evidence")
ACTION_STATUS = {
    "escalate": "escalated",
    "monitor": "monitor",
    "dismiss": "dismissed",
    "needs_evidence": "needs_evidence",
}
RULE_TITLES = {
    "R-DUP-001": "Same member, provider, code, date of service",
    "R-PTP-001": "Procedure-to-procedure unbundling (indicator 0)",
    "R-UNIT-001": "Units above synthetic MUE cap",
    "R-DEATH-001": "Date of service after date of death",
    "R-BH-001": "More than 960 billed minutes on one clinician-day",
    "R-IP-001": "Outpatient/ABA service during an inpatient stay",
    "R-EVV-001": "Home-health visit with no EVV row",
    "R-LEIE-001": "Billing NPI matches synthetic LEIE",
    "R-RX-001": "High-MME opioids across 4+ prescribers and pharmacies",
    "R-SEX-001": "Sex-incompatible synthetic procedure",
    "R-POS-001": "Office E/M billed at inpatient or ambulance POS",
    "R-AMB-001": "Overlapping ambulance trips same vehicle-day",
    "R-CLONE-001": "Identical paid amount cloned across many members same day",
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
    "doctor_shopping": "Doctor shopping",
    "sex_implausible": "Sex-implausible procedure",
    "pos_mismatch": "Place-of-service mismatch",
    "ambulance_overlap": "Overlapping ambulance trips",
    "clone_billing": "Clone billing",
    "em_upcode_z": "E/M mix vs peers",
    "hh_iqr": "Home-health volume fence",
    "genetic_mill": "Genetic-testing mill",
}
GAP_BY_KIND = {
    "evv_missing": "EVV visit records with the six CURES elements for the flagged home-health dates.",
    "after_death": "Date-of-death source and eligibility span overlapping the date of service.",
    "excluded_party": "LEIE match packet (NPI, name, exclusion type and effective date).",
    "duplicate": "Original vs resubmitted claim images for the duplicate member/provider/code/DOS set.",
    "ptp_pair": "Medical records supporting a PTP exception (modifier indicator is 0 in the synthetic table).",
    "unit_cap": "Documentation of units billed against the synthetic MUE cap.",
    "inpatient_overlap": "Inpatient census for the overlapping stay.",
    "clone_billing": "Source documentation for cloned paid amounts on the same day.",
    "daily_minutes_cap": "Clinician time log for the day that exceeds 960 billed minutes.",
    "doctor_shopping": "PDMP-equivalent fill history across the listed prescribers and pharmacies.",
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
    return {
        "alert_id": alert.alert_id,
        "detector": alert.detector,
        "rule_id": alert.rule_id,
        "rule_version": alert.rule_version,
        "rule_title": RULE_TITLES.get(alert.rule_id or "", alert.rule_id),
        "entity_id": alert.entity_id,
        "entity_type": alert.entity_type,
        "score": alert.score,
        "evidence": alert.evidence or {},
        "line_ids": alert.line_ids or [],
        "kind": kind,
        "label": KIND_LABELS.get(kind, kind.replace("_", " ") if kind else "Signal"),
    }


def evidence_gaps(alerts: list[Alert], case: Case) -> list[str]:
    gaps: list[str] = []
    kinds = {(a.evidence or {}).get("kind") for a in alerts}
    for kind in kinds:
        if isinstance(kind, str) and kind in GAP_BY_KIND:
            gaps.append(GAP_BY_KIND[kind])
    if case.evidence_strength < 0.4:
        gaps.append("Corroborating records to lift evidence strength above the 0.40 floor.")
    if not gaps:
        gaps.append("Medical records for the flagged claim lines, if the investigator still has residual uncertainty.")
    # unique, stable
    out: list[str] = []
    for g in gaps:
        if g not in out:
            out.append(g)
    return out


def serialize_case(session: Session, case: Case, user: User) -> dict[str, Any]:
    alerts = alerts_for(session, case.case_id)
    provider = session.get(Provider, case.primary_entity_id)
    decisions = list(
        session.execute(
            select(Decision).where(Decision.case_id == case.case_id).order_by(Decision.created_at.desc())
        ).scalars().all()
    )
    latest = decisions[0] if decisions else None
    return {
        "case_id": case.case_id,
        "run_id": case.run_id,
        "status": case.status,
        "lane": case.lane,
        "assignee_id": case.assignee_id,
        "primary_entity_id": case.primary_entity_id,
        "primary_entity_type": case.primary_entity_type,
        "primary_entity": _provider_card(provider, case.primary_entity_id),
        "harm": case.harm,
        "severity": case.severity,
        "members_affected": case.members_affected,
        "flagged_dollars": case.flagged_dollars,
        "evidence_strength": case.evidence_strength,
        "estimated_hours": case.estimated_hours,
        "p_confirm": case.p_confirm,
        "f30": case.f30,
        "f60": case.f60,
        "f90": case.f90,
        "alerts": [serialize_alert(a) for a in alerts],
        "evidence_gaps": evidence_gaps(alerts, case),
        "latest_decision": serialize_decision(latest) if latest else None,
        "latest_proposal": _latest_proposal(session, case.case_id),
        "latest_label": _latest_label(session, case.case_id),
        "member_unmask_permitted": can_unmask(user),
    }


def _latest_proposal(session: Session, case_id: str) -> dict[str, Any] | None:
    from claimshield.wiki.service import proposal_for_case, serialize_proposal

    row = proposal_for_case(session, case_id)
    return serialize_proposal(row) if row else None


def _latest_label(session: Session, case_id: str) -> dict[str, Any] | None:
    from claimshield.wiki.service import label_for_case, serialize_label

    row = label_for_case(session, case_id)
    return serialize_label(row) if row else None


def _provider_card(provider: Provider | None, fallback_id: str) -> dict[str, Any]:
    if provider is None:
        return {
            "provider_id": fallback_id,
            "name": fallback_id,
            "npi_syn": None,
            "specialty": None,
            "kind": None,
            "service_line": None,
        }
    return {
        "provider_id": provider.provider_id,
        "name": provider.name,
        "npi_syn": provider.npi_syn,
        "specialty": provider.specialty,
        "kind": provider.kind,
        "service_line": provider.service_line,
        "location_id": provider.location_id,
        "tin_token": provider.tin_token,
    }


def serialize_decision(row: Decision) -> dict[str, Any]:
    return {
        "decision_id": row.decision_id,
        "case_id": row.case_id,
        "actor_id": row.actor_id,
        "action": row.action,
        "ladder_step": row.ladder_step,
        "reason": row.reason,
        "evidence_refs": row.evidence_refs or [],
        "approved_by": row.approved_by,
        "created_at": iso(row.created_at),
    }


def claims_pack(session: Session, case: Case, user: User, *, unmask: bool) -> dict[str, Any]:
    alerts = alerts_for(session, case.case_id)
    lids = line_ids_for(alerts)
    reveal = unmask and can_unmask(user)
    if not lids:
        return {"case_id": case.case_id, "masked": not reveal, "rows": []}

    lines = list(session.execute(select(ClaimLine).where(ClaimLine.line_id.in_(lids))).scalars().all())
    claim_ids = {ln.claim_id for ln in lines}
    claims = {
        c.claim_id: c
        for c in session.execute(select(Claim).where(Claim.claim_id.in_(claim_ids))).scalars().all()
    }
    member_ids = {c.member_id for c in claims.values()}
    members = {
        m.member_id: m
        for m in session.execute(select(Member).where(Member.member_id.in_(member_ids))).scalars().all()
    }
    by_line: dict[str, list[dict[str, Any]]] = {}
    for alert in alerts:
        payload = serialize_alert(alert)
        for lid in alert.line_ids or []:
            by_line.setdefault(lid, []).append(
                {"alert_id": payload["alert_id"], "rule_id": payload["rule_id"], "label": payload["label"]}
            )

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
            }
        )
    rows.sort(key=lambda r: (r["dos_from"] or "", r["line_id"]))
    return {"case_id": case.case_id, "masked": not reveal, "rows": rows}


def evidence_item(session: Session, case: Case, item_id: str, user: User) -> dict[str, Any]:
    reveal = can_unmask(user)
    kind, _, rest = item_id.partition(":")
    if not rest:
        kind, rest = "alert", item_id
    if kind == "alert":
        alert = session.get(Alert, rest)
        if alert is None or alert.case_id != case.case_id:
            raise NotFound("evidence item not found")
        return {"item_id": item_id, "kind": "alert", "payload": serialize_alert(alert)}
    if kind == "line":
        pack = claims_pack(session, case, user, unmask=reveal)
        row = next((r for r in pack["rows"] if r["line_id"] == rest), None)
        if row is None:
            raise NotFound("evidence item not found")
        return {"item_id": item_id, "kind": "line", "payload": row}
    if kind == "claim":
        pack = claims_pack(session, case, user, unmask=reveal)
        rows = [r for r in pack["rows"] if r["claim_id"] == rest]
        if not rows:
            raise NotFound("evidence item not found")
        return {"item_id": item_id, "kind": "claim", "payload": {"claim_id": rest, "lines": rows}}
    if kind == "provider":
        provider = session.get(Provider, rest)
        if provider is None:
            raise NotFound("evidence item not found")
        return {"item_id": item_id, "kind": "provider", "payload": _provider_card(provider, rest)}
    if kind == "metric":
        return {
            "item_id": item_id,
            "kind": "metric",
            "payload": {
                "field": rest,
                "harm": case.harm,
                "severity": case.severity,
                "flagged_dollars": case.flagged_dollars,
                "members_affected": case.members_affected,
                "evidence_strength": case.evidence_strength,
                "p_confirm": case.p_confirm,
                "f30": case.f30,
                "f60": case.f60,
                "f90": case.f90,
                "estimated_hours": case.estimated_hours,
            },
        }
    if kind in ("prec", "precedent"):
        from claimshield.wiki.service import serialize_page

        page = session.get(WikiPage, rest)
        if page is None or page.status != "published":
            raise NotFound("evidence item not found")
        return {"item_id": item_id, "kind": "precedent", "payload": serialize_page(page)}
    raise NotFound("evidence item not found")


def _cite(item_id: str, kind: str, label: str) -> dict[str, str]:
    return {"id": item_id, "kind": kind, "label": label}


def template_brief(session: Session, case: Case, user: User) -> dict[str, Any]:
    alerts = alerts_for(session, case.case_id)
    serialized = [serialize_alert(a) for a in alerts]
    provider = session.get(Provider, case.primary_entity_id)
    name = provider.name if provider else case.primary_entity_id
    signal_cites = [
        _cite(f"alert:{a['alert_id']}", "alert", a["rule_id"] or a["detector"]) for a in serialized
    ]
    metric_cite = [_cite("metric:harm", "metric", "case metrics")]
    top_kind = serialized[0]["label"] if serialized else "detector output"
    kinds = sorted({a["label"] for a in serialized})
    n_lines = len(line_ids_for(alerts))
    why_lane = (
        "Harm override (harm ≥ 4) places this case in the harm-priority lane regardless of remaining hours."
        if case.lane == "harm_priority"
        else (
            "Evidence strength is below the 0.40 floor, so the knapsack left this case in needs-evidence."
            if case.lane == "needs_evidence"
            else (
                "The case sits in Monitor because it fell outside remaining investigator hours after knapsack fill."
                if case.lane == "overflow"
                else "The capacity knapsack selected this case on expected value within remaining hours."
            )
        )
    )
    if case.harm >= 4:
        action = "Escalate for human review of a potential FWA pattern requiring investigation."
    elif case.evidence_strength < 0.4:
        action = "Needs more evidence before a screening recommendation can be made."
    else:
        action = "Monitor pending investigator review of a potential FWA pattern requiring investigation."

    key_sentences = []
    for a in serialized[:8]:
        n = len(a["line_ids"])
        key_sentences.append(
            {
                "text": f"{a['label']} ({a['rule_id'] or a['detector']}) on {n} claim line(s) for entity {a['entity_id']}.",
                "cites": [_cite(f"alert:{a['alert_id']}", "alert", a["rule_id"] or a["detector"])],
            }
        )
    if not key_sentences:
        key_sentences.append(
            {
                "text": "No detector alerts are attached to this case.",
                "cites": metric_cite,
            }
        )

    timeline_text = (
        f"{n_lines} flagged claim lines form the chronological evidence for this case."
        if n_lines
        else "No flagged claim lines are attached; timeline is empty."
    )

    sections = [
        {
            "title": "Executive summary",
            "sentences": [
                {
                    "text": (
                        f"Case {case.case_id} is a potential FWA pattern requiring investigation involving "
                        f"{name} ({case.primary_entity_id}). {len(serialized)} detection signal(s) flag "
                        f"${case.flagged_dollars:,.0f} paid across {case.members_affected} member(s)."
                    ),
                    "cites": metric_cite + signal_cites[:3],
                }
            ],
        },
        {
            "title": "Why this case was surfaced",
            "sentences": [
                {
                    "text": f"Primary signal family: {top_kind}. Detector set: {', '.join(kinds) if kinds else 'none'}.",
                    "cites": signal_cites[:4] or metric_cite,
                },
                {"text": why_lane, "cites": metric_cite},
            ],
        },
        {"title": "Key evidence", "sentences": key_sentences},
        {
            "title": "Timeline",
            "sentences": [{"text": timeline_text, "cites": [_cite("metric:timeline", "metric", "flagged lines")]}],
        },
        {
            "title": "Risk / confidence",
            "sentences": [
                {
                    "text": (
                        f"P(confirm) {case.p_confirm:.0%}; evidence strength {case.evidence_strength:.0%}; "
                        f"30/60/90 risk {case.f30 if case.f30 is not None else '—'} / "
                        f"{case.f60 if case.f60 is not None else '—'} / "
                        f"{case.f90 if case.f90 is not None else '—'}."
                    ),
                    "cites": [_cite("metric:p_confirm", "metric", "risk scores")],
                },
                {
                    "text": "These scores are screening aids. They are not a fraud label.",
                    "cites": metric_cite,
                },
            ],
        },
        {
            "title": "Limitations",
            "sentences": [
                {
                    "text": "This brief is a template assembled only from stored case metrics and detector evidence. It does not use ground-truth labels as features.",
                    "cites": metric_cite,
                },
                {
                    "text": "Member identifiers are masked unless an investigator with member:unmask requests unmasking.",
                    "cites": metric_cite,
                },
            ],
        },
        {
            "title": "Recommended human-review action",
            "sentences": [{"text": action, "cites": metric_cite}],
        },
    ]
    from claimshield.wiki.service import match_precedents

    precedents = match_precedents(session, case)
    if precedents:
        sections.insert(
            3,
            {
                "title": "Matched precedents",
                "sentences": [
                    {
                        "text": (
                            f"{hit['title']}. {hit['why_it_matches']} "
                            f"Matching facts: {'; '.join(hit['matching_facts'])}. "
                            f"Source case {hit['source_case']}. Citation {hit['citation']}."
                        ),
                        "cites": [_cite(hit["citation"], "precedent", hit["title"][:48])],
                    }
                    for hit in precedents
                ],
            },
        )
    n_sents = sum(len(s["sentences"]) for s in sections)
    n_cited = sum(1 for s in sections for sent in s["sentences"] if sent["cites"])
    return {
        "case_id": case.case_id,
        "generator": "template",
        "confidence": case.p_confirm,
        "limitations": [
            "Template generator; LLM brief is not enabled on this run.",
            "Does not conclude fraud, waste, or abuse.",
        ],
        "action": action,
        "evidence_gaps": evidence_gaps(alerts, case),
        "precedents": precedents,
        "sections": sections,
        "validator": {"checked": n_sents, "dropped": 0, "cited": n_cited},
    }


def timeline_pack(session: Session, case: Case, user: User, *, unmask: bool) -> dict[str, Any]:
    alerts = alerts_for(session, case.case_id)
    lids = line_ids_for(alerts)
    reveal = unmask and can_unmask(user)
    events: list[dict[str, Any]] = []

    lines = list(session.execute(select(ClaimLine).where(ClaimLine.line_id.in_(lids))).scalars().all()) if lids else []
    claim_ids = {ln.claim_id for ln in lines}
    claims = {
        c.claim_id: c
        for c in session.execute(select(Claim).where(Claim.claim_id.in_(claim_ids))).scalars().all()
    } if claim_ids else {}
    members = {}
    if claims:
        mids = {c.member_id for c in claims.values()}
        members = {
            m.member_id: m
            for m in session.execute(select(Member).where(Member.member_id.in_(mids))).scalars().all()
        }
    line_signals: dict[str, list[str]] = {}
    for a in alerts:
        for lid in a.line_ids or []:
            line_signals.setdefault(lid, []).append(a.rule_id or a.detector)

    for ln in lines:
        claim = claims.get(ln.claim_id)
        member_id = claim.member_id if claim else ""
        member = members.get(member_id)
        disp = member_display(member_id, reveal, member.name if member else None)
        events.append(
            {
                "ts": iso(ln.dos_from),
                "kind": "claim",
                "flag": bool(line_signals.get(ln.line_id)),
                "ref": f"line:{ln.line_id}",
                "title": f"Claim line {ln.line_id} · {ln.code}",
                "detail": f"{disp['display']} · paid ${ln.paid:,.0f}",
                "entity_id": ln.rendering_provider_id,
            }
        )

    provider_ids = {case.primary_entity_id}
    for ln in lines:
        provider_ids.add(ln.rendering_provider_id)
        if claims.get(ln.claim_id) and claims[ln.claim_id].billing_provider_id:
            provider_ids.add(claims[ln.claim_id].billing_provider_id)

    refs = list(
        session.execute(
            select(Referral).where(
                (Referral.referring_id.in_(provider_ids)) | (Referral.receiving_id.in_(provider_ids))
            )
        ).scalars().all()
    )
    for ref in refs:
        events.append(
            {
                "ts": iso(ref.date),
                "kind": "referral",
                "flag": False,
                "ref": f"referral:{ref.id}",
                "title": f"Referral {ref.kind}",
                "detail": f"{ref.referring_id} → {ref.receiving_id}",
                "entity_id": ref.referring_id,
            }
        )

    subjects = list(
        session.execute(
            select(InvestigationSubject).where(InvestigationSubject.provider_id.in_(provider_ids))
        ).scalars().all()
    )
    inv_ids = {s.investigation_id for s in subjects}
    investigations = (
        list(session.execute(select(Investigation).where(Investigation.investigation_id.in_(inv_ids))).scalars().all())
        if inv_ids
        else []
    )
    for inv in investigations:
        events.append(
            {
                "ts": iso(inv.opened),
                "kind": "investigation",
                "flag": True,
                "ref": f"investigation:{inv.investigation_id}",
                "title": f"Prior investigation {inv.investigation_id}",
                "detail": inv.scheme_tag or inv.lead_source,
                "entity_id": case.primary_entity_id,
            }
        )
        if inv.closed:
            events.append(
                {
                    "ts": iso(inv.closed),
                    "kind": "investigation",
                    "flag": False,
                    "ref": f"investigation:{inv.investigation_id}:closed",
                    "title": f"Investigation closed {inv.investigation_id}",
                    "detail": inv.outcome or inv.closed_reason or "closed",
                    "entity_id": case.primary_entity_id,
                }
            )

    member_ids = {c.member_id for c in claims.values()}
    if member_ids:
        stays = list(
            session.execute(select(InpatientStay).where(InpatientStay.member_id.in_(member_ids))).scalars().all()
        )
        for stay in stays:
            disp = member_display(stay.member_id, reveal, None)
            events.append(
                {
                    "ts": iso(stay.admit),
                    "kind": "facility",
                    "flag": False,
                    "ref": f"stay:{stay.id}",
                    "title": f"Inpatient admit {stay.facility_id}",
                    "detail": f"{disp['display']} through {iso(stay.discharge)}",
                    "entity_id": stay.facility_id,
                }
            )

    events = [e for e in events if e.get("ts")]
    events.sort(key=lambda e: (e["ts"], e["kind"], e["ref"]))
    return {"case_id": case.case_id, "events": events}


def network_pack(session: Session, case: Case, user: User, *, hops: int = 2, unmask: bool = False) -> dict[str, Any]:
    hops = max(1, min(int(hops), 2))
    alerts = alerts_for(session, case.case_id)
    lids = line_ids_for(alerts)
    reveal = unmask and can_unmask(user)
    nodes: dict[str, dict[str, Any]] = {}
    edges: list[dict[str, Any]] = []
    edge_keys: set[tuple[str, str, str]] = set()

    def add_node(nid: str, ntype: str, label: str, **extra: Any) -> None:
        if nid not in nodes:
            nodes[nid] = {"id": nid, "type": ntype, "label": label, "primary": False, **extra}

    def add_edge(src: str, tgt: str, kind: str) -> None:
        if src == tgt:
            return
        a, b = (src, tgt) if src < tgt else (tgt, src)
        key = (a, b, kind)
        if key in edge_keys:
            return
        edge_keys.add(key)
        edges.append({"source": src, "target": tgt, "kind": kind})

    primary = case.primary_entity_id
    provider = session.get(Provider, primary)
    add_node(primary, "provider", provider.name if provider else primary, risk=case.p_confirm)
    nodes[primary]["primary"] = True

    lines = list(session.execute(select(ClaimLine).where(ClaimLine.line_id.in_(lids))).scalars().all()) if lids else []
    claim_ids = {ln.claim_id for ln in lines}
    claims = (
        list(session.execute(select(Claim).where(Claim.claim_id.in_(claim_ids))).scalars().all()) if claim_ids else []
    )
    claims_by_id = {c.claim_id: c for c in claims}

    seed_providers = {primary}
    seed_members: set[str] = set()
    seed_facilities: set[str] = set()
    for ln in lines:
        seed_providers.add(ln.rendering_provider_id)
        claim = claims_by_id.get(ln.claim_id)
        if claim:
            seed_providers.add(claim.billing_provider_id)
            seed_members.add(claim.member_id)
            if claim.facility_id:
                seed_facilities.add(claim.facility_id)

    providers = {
        p.provider_id: p
        for p in session.execute(select(Provider).where(Provider.provider_id.in_(seed_providers))).scalars().all()
    }
    for pid, p in providers.items():
        add_node(pid, "provider", p.name, specialty=p.specialty)

    member_rows = {
        m.member_id: m
        for m in session.execute(select(Member).where(Member.member_id.in_(seed_members))).scalars().all()
    } if seed_members else {}
    for mid in list(seed_members)[:40]:
        m = member_rows.get(mid)
        disp = member_display(mid, reveal, m.name if m else None)
        add_node(mid, "member", disp["display"], masked=disp["masked"])

    facilities = {
        f.facility_id: f
        for f in session.execute(select(Facility).where(Facility.facility_id.in_(seed_facilities))).scalars().all()
    } if seed_facilities else {}
    for fid in seed_facilities:
        fac = facilities.get(fid)
        add_node(fid, "facility", fac.type if fac else fid, facility_type=fac.type if fac else None)

    for ln in lines:
        claim = claims_by_id.get(ln.claim_id)
        if not claim:
            continue
        add_edge(ln.rendering_provider_id, claim.member_id, "rendered")
        add_edge(claim.billing_provider_id, claim.member_id, "billed")
        if claim.facility_id:
            add_edge(ln.rendering_provider_id, claim.facility_id, "at_facility")

    # hop-1/2: owners, referrals, shared location/tin
    loc_ids = {p.location_id for p in providers.values()}
    tin_ids = {p.tin_token for p in providers.values()}
    extra_providers = list(
        session.execute(
            select(Provider).where((Provider.location_id.in_(loc_ids)) | (Provider.tin_token.in_(tin_ids)))
        ).scalars().all()
    ) if loc_ids else []
    if hops >= 2:
        for p in extra_providers:
            add_node(p.provider_id, "provider", p.name, specialty=p.specialty)
            providers[p.provider_id] = p
            seed_providers.add(p.provider_id)

    by_loc: dict[str, list[str]] = {}
    by_tin: dict[str, list[str]] = {}
    for p in providers.values():
        by_loc.setdefault(p.location_id, []).append(p.provider_id)
        by_tin.setdefault(p.tin_token, []).append(p.provider_id)
    for ids in by_loc.values():
        for i, a in enumerate(ids):
            for b in ids[i + 1 :]:
                add_edge(a, b, "shared_location")
    for ids in by_tin.values():
        for i, a in enumerate(ids):
            for b in ids[i + 1 :]:
                add_edge(a, b, "shared_tin")

    links = list(
        session.execute(select(OwnershipLink).where(OwnershipLink.provider_id.in_(seed_providers))).scalars().all()
    )
    owner_ids = {lk.owner_id for lk in links}
    owners = {
        o.owner_id: o
        for o in session.execute(select(Owner).where(Owner.owner_id.in_(owner_ids))).scalars().all()
    } if owner_ids else {}
    for lk in links:
        owner = owners.get(lk.owner_id)
        add_node(lk.owner_id, "owner", owner.name if owner else lk.owner_id, owner_kind=owner.kind if owner else None)
        add_edge(lk.owner_id, lk.provider_id, "owns")

    refs = list(
        session.execute(
            select(Referral).where(
                (Referral.referring_id.in_(seed_providers)) | (Referral.receiving_id.in_(seed_providers))
            )
        ).scalars().all()
    )
    for ref in refs:
        if ref.referring_id not in nodes:
            rp = session.get(Provider, ref.referring_id)
            add_node(ref.referring_id, "provider", rp.name if rp else ref.referring_id)
        if ref.receiving_id not in nodes:
            rp = session.get(Provider, ref.receiving_id)
            add_node(ref.receiving_id, "provider", rp.name if rp else ref.receiving_id)
        add_edge(ref.referring_id, ref.receiving_id, "referral")

    node_list = list(nodes.values())
    if len(node_list) > 80:
        keep = {primary}
        for n in node_list:
            if n["type"] in {"provider", "owner", "facility"}:
                keep.add(n["id"])
        members = [n for n in node_list if n["type"] == "member"]
        keep.update(m["id"] for m in members[:20])
        node_list = [n for n in node_list if n["id"] in keep]
        keep_ids = {n["id"] for n in node_list}
        edges = [e for e in edges if e["source"] in keep_ids and e["target"] in keep_ids]

    return {
        "case_id": case.case_id,
        "hops": hops,
        "primary_entity_id": primary,
        "nodes": node_list,
        "edges": edges,
    }


def record_decision(
    session: Session,
    *,
    case: Case,
    user: User,
    action: str,
    reason: str,
    ladder_step: str | None,
    evidence_refs: list[str],
    now: datetime,
) -> dict[str, Any]:
    if action not in ACTIONS:
        raise ValidationFailed("action must be escalate, monitor, dismiss, or needs_evidence")
    text = (reason or "").strip()
    if len(text) < 20:
        raise ValidationFailed("reason must be at least 20 characters")
    case.status = ACTION_STATUS[action]
    row = Decision(
        decision_id=new_id("DEC"),
        case_id=case.case_id,
        actor_id=user.id,
        action=action,
        ladder_step=ladder_step,
        reason=text,
        evidence_refs=evidence_refs,
        approved_by=None,
        created_at=now,
    )
    session.add(row)
    event = append_event(
        session,
        actor_id=user.id,
        role=user.role,
        action="case.decide",
        object_type="case",
        object_id=case.case_id,
        payload={
            "decision_id": row.decision_id,
            "action": action,
            "status": case.status,
            "ladder_step": ladder_step,
        },
        ts=now,
    )
    session.flush()
    from claimshield.wiki.service import draft_precedent, serialize_label, serialize_proposal

    proposal, label = draft_precedent(session, case=case, decision=row, user=user, now=now)
    verification = chain_status(session)
    return {
        "decision_id": row.decision_id,
        "case_id": case.case_id,
        "action": action,
        "status": case.status,
        "reason": text,
        "ladder_step": ladder_step,
        "evidence_refs": evidence_refs,
        "created_at": iso(row.created_at),
        "audit": {
            "seq": event.seq,
            "hash": event.hash,
            "prev_hash": event.prev_hash,
            "ts": iso(event.ts),
            "action": event.action,
            "actor": user.display_name,
            "actor_id": user.id,
            "case_id": case.case_id,
            "reason": text,
            "chain_intact": verification["intact"],
            "last_seq": verification["last_seq"],
        },
        "proposal": serialize_proposal(proposal),
        "label": serialize_label(label),
        "note": "Potential FWA pattern requiring investigation. This is not an automatic fraud label.",
    }
