"""Case investigation pack: case summary, claims, template brief, timeline, overrides."""

from __future__ import annotations

from datetime import datetime
from typing import Any

from sqlalchemy import select
from sqlalchemy.orm import Session

from claimshield.audit.service import append_event, chain_status
from claimshield.auth.rbac import has_permission
from claimshield.cases.common import (
    alerts_for,
    audit_unmask,
    can_unmask,
    claim_rows,
    iso,
    line_ids_for,
    member_display,
    serialize_alert,
)
from claimshield.cases.decisions import (
    allowed_actions,
    decision_block_reason,
    decision_options,
    pending_decision,
    serialize_decision,
)
from claimshield.cases.network import network_edge, node_detail
from claimshield.cases.provenance import alert_lineage, case_provenance, grouping_from_alerts
from claimshield.core.errors import Forbidden, NotFound, ValidationFailed
from claimshield.core.ids import new_id
from claimshield.db.models import (
    Alert,
    Batch,
    Case,
    Claim,
    ClaimLine,
    Decision,
    InpatientStay,
    Investigation,
    InvestigationSubject,
    Member,
    PipelineRun,
    Provider,
    QueueOverride,
    Referral,
    User,
    WikiPage,
)
from claimshield.queue.explain import LANE_LABELS, override_text, screening_days_left, why_rank
from claimshield.queue.rank import rank_pack_for_case, recommendation_for
from claimshield.risk.present import case_risk, risk_fields, score_label
from claimshield.wiki.service import (
    label_for_case,
    match_precedents,
    proposal_for_case,
    serialize_label,
    serialize_page,
    serialize_proposal,
)

GAP_BY_KIND = {
    "evv_missing": "EVV visit records with the six CURES elements for the flagged home-health dates.",
    "after_death": "Date-of-death source and eligibility span overlapping the date of service.",
    "excluded_party": "LEIE match packet (NPI, name, exclusion type and effective date).",
    "duplicate": "Original vs resubmitted claim images for the duplicate member/provider/code/DOS set.",
    "ptp_pair": (
        "Indicator 0: the column-two code is not separately payable with the column-one code under any "
        "modifier. Request the claim images to confirm the pair was paid together and the amount to recover. "
        "(For indicator-1 pairs, request records supporting a distinct-procedural-service modifier.)"
    ),
    "unit_cap": "Documentation of units billed against the synthetic MUE cap.",
    "inpatient_overlap": "Inpatient census for the overlapping stay.",
    "clone_billing": (
        "Visit notes for a sample of the same-day services, to check volume against staffing and for "
        "cloned documentation."
    ),
    "ambulance_overlap": (
        "Trip sheets with vehicle, crew, pickup and drop-off times; the extract cannot test overlap."
    ),
    "sex_implausible": (
        "Coding check only: confirm the member's sex on file and whether a KX modifier or condition code 45 "
        "was omitted. Not evidence of FWA."
    ),
    "daily_minutes_cap": "Clinician time log for the day that exceeds 960 billed minutes.",
    "doctor_shopping": (
        "PDMP-equivalent fill history across the listed prescribers and pharmacies; consider pharmacy "
        "lock-in or care-coordination review for the member."
    ),
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
        session.execute(select(Decision).where(Decision.case_id == case.case_id).order_by(Decision.created_at.desc()))
        .scalars()
        .all()
    )
    latest = decisions[0] if decisions else None
    pending = pending_decision(session, case.case_id)
    peers = list(session.execute(select(Case).where(Case.run_id == case.run_id)).scalars().all())
    run = session.get(PipelineRun, case.run_id)
    member_weight = float((run.summary or {}).get("member_weight") or 1.0) if run else 1.0
    horizon = int(run.horizon_days or 60) if run else 60
    factors = rank_pack_for_case(case, horizon_days=horizon, peers=peers, member_weight=member_weight)
    override = (
        session.execute(
            select(QueueOverride).where(QueueOverride.case_id == case.case_id).order_by(QueueOverride.created_at.desc())
        )
        .scalars()
        .first()
    )
    shown = override if override and override.action != "release" else None
    entity_ids = case.entity_ids or [case.primary_entity_id]
    grouping = grouping_from_alerts(alerts, entity_ids)
    why = why_rank(case, factors)
    batch = session.get(Batch, run.batch_id) if run is not None else None
    provenance = case_provenance(
        case=case,
        alerts=alerts,
        run=run,
        batch=batch,
        grouping=grouping,
        why_rank_text=str(why.get("text") or ""),
    )
    return {
        "case_id": case.case_id,
        "run_id": case.run_id,
        "status": case.status,
        "lane": case.lane,
        "assignee_id": case.assignee_id,
        "primary_entity_id": case.primary_entity_id,
        "primary_entity_type": case.primary_entity_type,
        "entity_ids": entity_ids,
        "primary_entity": _provider_card(provider, case.primary_entity_id),
        "harm": case.harm,
        "priority_override": bool(case.override_kinds) or case.harm >= 4,
        "override_kinds": case.override_kinds or [],
        "lane_label": LANE_LABELS.get(case.lane, case.lane),
        "severity": case.severity,
        "members_affected": case.members_affected,
        "flagged_dollars": case.flagged_dollars,
        "evidence_strength": case.evidence_strength,
        "estimated_hours": case.estimated_hours,
        "p_confirm": case.p_confirm,
        "expected_value": getattr(case, "expected_value", None) or 0.0,
        "f30": case.f30,
        "f60": case.f60,
        "f90": case.f90,
        **risk_fields(case, case_risk(session, case.case_id)),
        "sla_due": iso(case.sla_due),
        "screening_days_left": screening_days_left(case),
        "rank_factors": factors,
        "recommendation": recommendation_for(case.lane),
        "why_rank": why,
        "override": (
            {
                "action": shown.action,
                "reason": shown.reason,
                "actor_id": shown.actor_id,
                "prior_lane": shown.prior_lane,
            }
            if shown
            else None
        ),
        "alerts": [serialize_alert(a) for a in alerts],
        "evidence_gaps": evidence_gaps(alerts, case),
        "latest_decision": serialize_decision(latest) if latest else None,
        "pending_decision": serialize_decision(pending) if pending else None,
        "allowed_actions": allowed_actions(session, case, user),
        "can_decide": decision_block_reason(case, user) is None,
        "decision_blocked_reason": decision_block_reason(case, user),
        "decision_options": decision_options(),
        "latest_proposal": _latest_proposal(session, case.case_id),
        "latest_label": _latest_label(session, case.case_id),
        "member_unmask_permitted": can_unmask(user),
        "can_assign": has_permission(user.role, "case:assign") or has_permission(user.role, "admin:*"),
        "suspicion_only": True,
        "grouping": grouping,
        "provenance": provenance,
    }


def _latest_proposal(session: Session, case_id: str) -> dict[str, Any] | None:
    row = proposal_for_case(session, case_id)
    return serialize_proposal(row) if row else None


def _latest_label(session: Session, case_id: str) -> dict[str, Any] | None:
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


def claims_pack(
    session: Session,
    case: Case,
    user: User,
    *,
    unmask: bool,
    audit: bool = True,
) -> dict[str, Any]:
    alerts = alerts_for(session, case.case_id)
    reveal = (
        audit_unmask(session, user=user, case=case, surface="claims", unmask=unmask)
        if audit
        else (unmask and can_unmask(user))
    )
    return {"case_id": case.case_id, "masked": not reveal, "rows": claim_rows(session, alerts, reveal=reveal)}


def evidence_item(session: Session, case: Case, item_id: str, user: User) -> dict[str, Any]:
    # Evidence cards are masked; member identity is revealed only through the audited unmask paths.
    reveal = False
    kind, _, rest = item_id.partition(":")
    if not rest:
        kind, rest = "alert", item_id
    if kind == "alert":
        alert = session.get(Alert, rest)
        if alert is None or alert.case_id != case.case_id:
            raise NotFound("evidence item not found")
        packed = serialize_alert(alert)
        packed["lineage"] = alert_lineage(alert)
        return {"item_id": item_id, "kind": "alert", "payload": packed}
    if kind == "line":
        pack = claims_pack(session, case, user, unmask=reveal, audit=False)
        row = next((r for r in pack["rows"] if r["line_id"] == rest), None)
        if row is None:
            raise NotFound("evidence item not found")
        return {"item_id": item_id, "kind": "line", "payload": row}
    if kind == "claim":
        pack = claims_pack(session, case, user, unmask=reveal, audit=False)
        rows = [r for r in pack["rows"] if r["claim_id"] == rest]
        if not rows:
            raise NotFound("evidence item not found")
        return {"item_id": item_id, "kind": "claim", "payload": {"claim_id": rest, "lines": rows}}
    if kind == "provider":
        provider = session.get(Provider, rest)
        if provider is None:
            raise NotFound("evidence item not found")
        node_detail(session, case, user, rest)  # raises NotFound when the provider is outside the case network
        return {"item_id": item_id, "kind": "provider", "payload": _provider_card(provider, rest)}
    if kind == "node":
        detail = node_detail(session, case, user, rest)
        return {"item_id": item_id, "kind": "node", "payload": detail.model_dump(exclude_none=True)}
    if kind == "edge":
        edge = network_edge(session, case, user, rest)
        return {"item_id": item_id, "kind": "edge", "payload": edge.model_dump(exclude_none=True)}
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
        page = session.get(WikiPage, rest)
        if page is None or page.status != "published":
            raise NotFound("evidence item not found")
        return {"item_id": item_id, "kind": "precedent", "payload": serialize_page(page)}
    raise NotFound("evidence item not found")


BRIEF_LIMITATIONS = [
    "Template generator; LLM brief is not enabled on this run.",
    "Generated from synthetic data; no medical records were reviewed.",
    "Scores are heuristic and uncalibrated.",
    "Signals have common legitimate explanations; see the evidence gaps.",
    "This brief is not a determination of improper payment or fraud; a human investigator decides.",
]
CITABLE_METRICS = frozenset({"harm", "timeline", "p_confirm", "severity", "flagged_dollars", "evidence_strength"})


def validate_citations(
    sections: list[dict[str, Any]], *, alert_ids: set[str], precedents: list[dict[str, Any]]
) -> dict[str, Any]:
    """Drop sentences whose citations do not resolve to this case's alerts, metrics or precedents.

    Mutates ``sections`` in place. It checks citation ids only; numbers inside sentences are not
    re-derived from the evidence pack.
    """
    known_precedents = {str(p.get("citation")) for p in precedents}
    checked = dropped = cited = 0
    reasons: list[str] = []
    for section in sections:
        kept = []
        for sentence in section["sentences"]:
            checked += 1
            bad = [c["id"] for c in sentence["cites"] if not _cite_resolves(c["id"], alert_ids, known_precedents)]
            if not sentence["cites"] or bad:
                dropped += 1
                reasons.append(f"{section['title']}: {'unresolved ' + ', '.join(bad) if bad else 'no citation'}")
                continue
            cited += 1
            kept.append(sentence)
        section["sentences"] = kept
    sections[:] = [s for s in sections if s["sentences"]]
    return {
        "checked": checked,
        "dropped": dropped,
        "cited": cited,
        "dropped_reasons": reasons[:20],
        "method": "Each citation id must resolve to this case's alerts, metrics or matched precedents; "
        "numbers in sentences are not re-checked.",
    }


def _cite_resolves(item_id: str, alert_ids: set[str], precedents: set[str]) -> bool:
    kind, _, rest = item_id.partition(":")
    if kind == "alert":
        return rest in alert_ids
    if kind == "metric":
        return rest in CITABLE_METRICS
    if kind == "prec":
        return item_id in precedents
    return False


def _cite(item_id: str, kind: str, label: str) -> dict[str, str]:
    return {"id": item_id, "kind": kind, "label": label}


def template_brief(session: Session, case: Case, user: User) -> dict[str, Any]:
    alerts = alerts_for(session, case.case_id)
    serialized = [serialize_alert(a) for a in alerts]
    provider = session.get(Provider, case.primary_entity_id)
    name = provider.name if provider else case.primary_entity_id
    signal_cites = [_cite(f"alert:{a['alert_id']}", "alert", a["rule_id"] or a["detector"]) for a in serialized]
    metric_cite = [_cite("metric:harm", "metric", "case metrics")]
    top_kind = serialized[0]["label"] if serialized else "detector output"
    approaches = ", ".join(sorted({str(a.get("approach") or a["detector"]) for a in serialized}))
    n_lines = len(line_ids_for(alerts))
    why_lane = (
        override_text(case)
        if case.lane == "harm_priority"
        else (
            "Evidence strength is below the 0.40 floor, so the knapsack left this case in needs-evidence."
            if case.lane == "needs_evidence"
            else (
                "The case is on the tracked backlog because it fell outside remaining investigator hours "
                "after knapsack fill."
                if case.lane == "overflow"
                else "The capacity knapsack selected this case on its combined rank score within remaining hours."
            )
        )
    )
    if case.primary_entity_type == "member":
        action = (
            "Refer this member-level pattern for pharmacy lock-in or care-coordination review; "
            "prescribers and pharmacies are context, not subjects."
        )
    elif case.harm >= 4 or case.override_kinds:
        action = "Escalate for human review of a potential FWA pattern requiring investigation."
    elif case.evidence_strength < 0.4:
        action = "Needs more evidence before a screening recommendation can be made."
    else:
        action = "Monitor pending investigator review of a potential FWA pattern requiring investigation."

    key_sentences = []
    for a in serialized[:8]:
        n = len(a["line_ids"])
        policy = a.get("policy_ref")
        policy_bit = f" Policy {policy}." if policy else ""
        key_sentences.append(
            {
                "text": (
                    f"{a['label']} ({a['rule_id'] or a['detector']}) on {n} claim line(s) "
                    f"for entity {a['entity_id']}.{policy_bit}"
                ),
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
                    "text": (
                        f"Primary signal family: {top_kind}. "
                        f"Approaches used: {approaches or 'none'}. "
                        "A flag is a reason to review evidence, not a finding of fraud."
                    ),
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
                        f"P(confirm) {case.p_confirm:.0%} ({score_label(case_risk(session, case.case_id))}); "
                        f"evidence strength {case.evidence_strength:.0%}; "
                        f"30/60/90-day risk {case.f30 if case.f30 is not None else '—'} / "
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
                    "text": (
                        "This brief is a template assembled only from stored case metrics and detector evidence. "
                        "It does not use ground-truth labels as features."
                    ),
                    "cites": metric_cite,
                },
                {
                    "text": (
                        "Member identifiers are masked unless an investigator with member:unmask requests unmasking."
                    ),
                    "cites": metric_cite,
                },
            ],
        },
        {
            "title": "Recommended human-review action",
            "sentences": [
                {"text": action, "cites": metric_cite},
                {
                    "text": (
                        "Action ladder is education letter, records request, then escalation to the "
                        "State Medicaid agency program integrity unit, which decides on MFCU referral, "
                        "prepayment review, or a 42 CFR 455.23 payment suspension. Every escalation "
                        "needs manager approval. ClaimShield only recommends."
                    ),
                    "cites": metric_cite,
                },
            ],
        },
    ]
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
    validator = validate_citations(sections, alert_ids={a["alert_id"] for a in serialized}, precedents=precedents)
    return {
        "case_id": case.case_id,
        "generator": "template",
        "confidence": case.p_confirm,
        "limitations": BRIEF_LIMITATIONS,
        "action": action,
        "evidence_gaps": evidence_gaps(alerts, case),
        "precedents": precedents,
        "sections": sections,
        "validator": validator,
    }


def timeline_pack(session: Session, case: Case, user: User, *, unmask: bool) -> dict[str, Any]:
    alerts = alerts_for(session, case.case_id)
    lids = line_ids_for(alerts)
    reveal = audit_unmask(session, user=user, case=case, surface="timeline", unmask=unmask)
    events: list[dict[str, Any]] = []

    lines = list(session.execute(select(ClaimLine).where(ClaimLine.line_id.in_(lids))).scalars().all()) if lids else []
    claim_ids = {ln.claim_id for ln in lines}
    claims = (
        {c.claim_id: c for c in session.execute(select(Claim).where(Claim.claim_id.in_(claim_ids))).scalars().all()}
        if claim_ids
        else {}
    )
    members = {}
    if claims:
        mids = {c.member_id for c in claims.values()}
        members = {
            m.member_id: m for m in session.execute(select(Member).where(Member.member_id.in_(mids))).scalars().all()
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
        )
        .scalars()
        .all()
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
        session.execute(select(InvestigationSubject).where(InvestigationSubject.provider_id.in_(provider_ids)))
        .scalars()
        .all()
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


OVERRIDE_ACTIONS = ("promote", "defer", "release")


def record_rank_override(
    session: Session,
    *,
    case: Case,
    user: User,
    action: str,
    reason: str,
    now: datetime,
) -> dict[str, Any]:
    if not (
        has_permission(user.role, "queue:configure")
        or has_permission(user.role, "case:decide")
        or has_permission(user.role, "admin:*")
    ):
        raise Forbidden("role cannot override queue rank")
    if action not in OVERRIDE_ACTIONS:
        raise ValidationFailed("action must be promote, defer, or release")
    text = (reason or "").strip()
    if len(text) < 20:
        raise ValidationFailed("reason must be at least 20 characters")
    if case.status in {"dismissed", "escalated"}:
        raise ValidationFailed("a closed case is not re-queued here")
    prior = case.lane
    if action == "promote":
        if case.lane in {"harm_priority", "selected"}:
            raise ValidationFailed("case is already in today's recommended queue")
        case.lane = "selected"
    elif action == "defer":
        if case.lane == "overflow":
            raise ValidationFailed("case is already on the tracked backlog")
        case.lane = "overflow"
    else:
        latest = (
            session.execute(
                select(QueueOverride)
                .where(QueueOverride.case_id == case.case_id)
                .order_by(QueueOverride.created_at.desc())
            )
            .scalars()
            .first()
        )
        if latest is None or latest.action == "release":
            raise ValidationFailed("no override to release")
        case.lane = latest.prior_lane
    row = QueueOverride(
        override_id=new_id("QOV"),
        case_id=case.case_id,
        run_id=case.run_id,
        actor_id=user.id,
        action=action,
        reason=text,
        prior_lane=prior,
        created_at=now,
    )
    session.add(row)
    event = append_event(
        session,
        actor_id=user.id,
        role=user.role,
        action="queue.override",
        object_type="case",
        object_id=case.case_id,
        payload={
            "override_id": row.override_id,
            "action": action,
            "prior_lane": prior,
            "lane": case.lane,
            "status": case.status,
        },
        ts=now,
    )
    session.flush()
    verification = chain_status(session)
    return {
        "case_id": case.case_id,
        "lane": case.lane,
        "status": case.status,
        "recommendation": recommendation_for(case.lane),
        "override": {
            "action": action,
            "reason": text,
            "actor_id": user.id,
            "prior_lane": prior,
        },
        "audit": {
            "seq": event.seq,
            "hash": event.hash,
            "prev_hash": event.prev_hash,
            "ts": iso(event.ts),
            "action": event.action,
            "chain_intact": verification["intact"],
        },
        "note": "Human override recorded. Overflow stays open on the tracked backlog and is not a dismissal.",
    }


def assign_case(
    session: Session,
    *,
    case: Case,
    user: User,
    assignee_id: str,
    now: datetime,
) -> dict[str, Any]:
    if not has_permission(user.role, "case:assign") and not has_permission(user.role, "admin:*"):
        raise Forbidden("role lacks case:assign")
    if user.role == "investigator" and assignee_id != user.id:
        raise Forbidden("investigators may only take ownership of a case")
    if user.role == "investigator" and case.assignee_id not in (None, user.id):
        raise Forbidden("case is owned by another investigator; ask a manager to reassign it")
    assignee = session.get(User, assignee_id)
    if assignee is None or not assignee.is_active:
        raise ValidationFailed("assignee not found")
    case.assignee_id = assignee.id
    append_event(
        session,
        actor_id=user.id,
        role=user.role,
        action="case.assign",
        object_type="case",
        object_id=case.case_id,
        payload={"assignee_id": assignee.id, "assignee": assignee.display_name},
        ts=now,
    )
    session.flush()
    return serialize_case(session, case, user)
