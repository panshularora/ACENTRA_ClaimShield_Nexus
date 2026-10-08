"""Precedent proposals, labels, and structured retrieval (no invented similarity)."""

from __future__ import annotations

from datetime import UTC, datetime
from typing import Any

from sqlalchemy import select
from sqlalchemy.orm import Session

from claimshield.audit.service import append_event
from claimshield.cases.workspace import KIND_LABELS, RULE_TITLES, alerts_for, iso, serialize_alert
from claimshield.core.errors import Conflict, NotFound, ValidationFailed
from claimshield.core.ids import new_id
from claimshield.db.models import Case, Decision, Label, Provider, User, WikiPage, WikiProposal


def _scheme_tags(alerts: list) -> list[str]:
    tags: list[str] = []
    for alert in alerts:
        kind = (alert.evidence or {}).get("kind")
        if isinstance(kind, str) and kind and kind not in tags:
            tags.append(kind)
    return tags


def _rule_ids(alerts: list) -> list[str]:
    ids: list[str] = []
    for alert in alerts:
        if alert.rule_id and alert.rule_id not in ids:
            ids.append(alert.rule_id)
    return ids


def serialize_proposal(row: WikiProposal) -> dict[str, Any]:
    return {
        "proposal_id": row.proposal_id,
        "kind": row.kind,
        "status": row.status,
        "title": row.title,
        "source_case_id": row.source_case_id,
        "decision_id": row.decision_id,
        "body": row.body or {},
        "banner": "Proposed precedent — awaiting approval" if row.status == "pending" else None,
        "created_by": row.created_by,
        "created_at": iso(row.created_at),
        "reviewed_by": row.reviewed_by,
        "reviewed_at": iso(row.reviewed_at),
        "review_note": row.review_note,
        "page_id": row.page_id,
    }


def serialize_page(row: WikiPage) -> dict[str, Any]:
    return {
        "page_id": row.page_id,
        "slug": row.slug,
        "type": row.type,
        "title": row.title,
        "status": row.status,
        "body": row.body or {},
        "source_proposal_id": row.source_proposal_id,
        "created_at": iso(row.created_at),
        "approved_by": row.approved_by,
    }


def serialize_label(row: Label) -> dict[str, Any]:
    return {
        "label_id": row.label_id,
        "case_id": row.case_id,
        "decision_id": row.decision_id,
        "action": row.action,
        "status": row.status,
        "scheme_tags": row.scheme_tags or [],
        "rule_ids": row.rule_ids or [],
        "created_at": iso(row.created_at),
        "approved_by": row.approved_by,
        "approved_at": iso(row.approved_at),
    }


def draft_precedent(
    session: Session,
    *,
    case: Case,
    decision: Decision,
    user: User,
    now: datetime,
) -> tuple[WikiProposal, Label]:
    alerts = alerts_for(session, case.case_id)
    serialized = [serialize_alert(a) for a in alerts]
    tags = _scheme_tags(alerts)
    rules = _rule_ids(alerts)
    provider = session.get(Provider, case.primary_entity_id)
    pattern = [KIND_LABELS.get(t, t.replace("_", " ")) for t in tags] or ["unspecified detector pattern"]
    top = pattern[0]
    line_ids: list[str] = []
    for a in alerts:
        for lid in a.line_ids or []:
            if lid not in line_ids:
                line_ids.append(lid)
    title = f"Precedent: {decision.action} · {top}"
    body = {
        "source_case": case.case_id,
        "primary_entity_type": case.primary_entity_type,
        "primary_entity_id": case.primary_entity_id,
        "primary_entity_name": provider.name if provider else case.primary_entity_id,
        "decision": decision.action,
        "outcome": case.status,
        "confirmed_pattern": pattern,
        "scheme_tags": tags,
        "rules": [
            {"rule_id": r, "title": RULE_TITLES.get(r, r)}
            for r in rules
        ],
        "key_evidence": [
            {
                "alert_id": a["alert_id"],
                "rule_id": a["rule_id"],
                "label": a["label"],
                "line_count": len(a["line_ids"]),
            }
            for a in serialized[:12]
        ],
        "supporting_line_ids": line_ids[:40],
        "rationale": decision.reason,
        "limitations": [
            "Human screening decision, not an automatic fraud label.",
            "Template precedent drafted from stored detector evidence only.",
            "Ground-truth scheme labels are not used as features.",
        ],
        "changes": [
            f"New precedent page from case {case.case_id}.",
            f"Outcome {decision.action} pending manager/analyst approval.",
        ],
        "sources": [
            {"kind": "case", "id": case.case_id},
            {"kind": "decision", "id": decision.decision_id},
            *[{"kind": "rule", "id": r} for r in rules],
        ],
    }
    proposal = WikiProposal(
        proposal_id=new_id("PROP"),
        kind="precedent",
        status="pending",
        title=title,
        source_case_id=case.case_id,
        decision_id=decision.decision_id,
        body=body,
        created_by=user.id,
        created_at=now,
    )
    label = Label(
        label_id=new_id("LBL"),
        case_id=case.case_id,
        decision_id=decision.decision_id,
        action=decision.action,
        status="pending",
        scheme_tags=tags,
        rule_ids=rules,
        created_at=now,
    )
    session.add(proposal)
    session.add(label)
    session.flush()
    append_event(
        session,
        actor_id=user.id,
        role=user.role,
        action="wiki.propose",
        object_type="wiki_proposal",
        object_id=proposal.proposal_id,
        payload={"case_id": case.case_id, "decision_id": decision.decision_id, "kind": "precedent"},
        ts=now,
    )
    return proposal, label


def list_proposals(session: Session, *, status: str | None = None) -> list[WikiProposal]:
    stmt = select(WikiProposal).order_by(WikiProposal.created_at.desc())
    if status:
        stmt = stmt.where(WikiProposal.status == status)
    return list(session.execute(stmt).scalars().all())


def get_proposal(session: Session, proposal_id: str) -> WikiProposal:
    row = session.get(WikiProposal, proposal_id)
    if row is None:
        raise NotFound("proposal not found")
    return row


def get_page(session: Session, slug_or_id: str) -> WikiPage:
    row = session.get(WikiPage, slug_or_id)
    if row is not None:
        return row
    row = session.execute(select(WikiPage).where(WikiPage.slug == slug_or_id)).scalar_one_or_none()
    if row is None:
        raise NotFound("wiki page not found")
    return row


def list_pages(session: Session, *, page_type: str | None = None) -> list[WikiPage]:
    stmt = select(WikiPage).where(WikiPage.status == "published").order_by(WikiPage.created_at.desc())
    if page_type:
        stmt = stmt.where(WikiPage.type == page_type)
    return list(session.execute(stmt).scalars().all())


def _linked_label(session: Session, decision_id: str) -> Label | None:
    return session.execute(select(Label).where(Label.decision_id == decision_id)).scalar_one_or_none()


def approve_proposal(session: Session, *, proposal: WikiProposal, user: User, note: str, now: datetime) -> WikiPage:
    if proposal.status != "pending":
        raise Conflict("proposal is not pending")
    page = WikiPage(
        page_id=new_id("PAGE"),
        slug=f"precedent-{proposal.decision_id.lower()}",
        type="precedent",
        title=proposal.title.replace("Proposed ", "").replace("proposed ", ""),
        status="published",
        body=proposal.body or {},
        source_proposal_id=proposal.proposal_id,
        created_at=now,
        approved_by=user.id,
    )
    session.add(page)
    proposal.status = "approved"
    proposal.reviewed_by = user.id
    proposal.reviewed_at = now
    proposal.review_note = note
    proposal.page_id = page.page_id
    label = _linked_label(session, proposal.decision_id)
    if label is not None:
        label.status = "approved"
        label.approved_by = user.id
        label.approved_at = now
    decision = session.get(Decision, proposal.decision_id)
    if decision is not None:
        decision.approved_by = user.id
    session.flush()
    append_event(
        session,
        actor_id=user.id,
        role=user.role,
        action="wiki.approve",
        object_type="wiki_page",
        object_id=page.page_id,
        payload={
            "proposal_id": proposal.proposal_id,
            "case_id": proposal.source_case_id,
            "label_id": label.label_id if label else None,
        },
        ts=now,
    )
    return page


def reject_proposal(session: Session, *, proposal: WikiProposal, user: User, note: str, now: datetime) -> WikiProposal:
    if proposal.status != "pending":
        raise Conflict("proposal is not pending")
    text = (note or "").strip()
    if len(text) < 20:
        raise ValidationFailed("reject note must be at least 20 characters")
    proposal.status = "rejected"
    proposal.reviewed_by = user.id
    proposal.reviewed_at = now
    proposal.review_note = text
    label = _linked_label(session, proposal.decision_id)
    if label is not None:
        label.status = "rejected"
    session.flush()
    append_event(
        session,
        actor_id=user.id,
        role=user.role,
        action="wiki.reject",
        object_type="wiki_proposal",
        object_id=proposal.proposal_id,
        payload={"case_id": proposal.source_case_id},
        ts=now,
    )
    return proposal


def match_precedents(session: Session, case: Case) -> list[dict[str, Any]]:
    """Return approved precedents that share stored rule ids or signal kinds. No scores."""
    alerts = alerts_for(session, case.case_id)
    rule_ids = set(_rule_ids(alerts))
    kinds = set(_scheme_tags(alerts))
    pages = list_pages(session, page_type="precedent")
    hits: list[dict[str, Any]] = []
    for page in pages:
        body = page.body or {}
        if body.get("source_case") == case.case_id:
            continue
        page_rules = {r.get("rule_id") for r in body.get("rules") or [] if isinstance(r, dict) and r.get("rule_id")}
        page_kinds = set(body.get("scheme_tags") or [])
        shared_rules = sorted(rule_ids & page_rules)
        shared_kinds = sorted(kinds & page_kinds)
        facts: list[str] = []
        for rid in shared_rules:
            facts.append(f"Shared rule {rid}" + (f" ({RULE_TITLES.get(rid)})" if RULE_TITLES.get(rid) else ""))
        for kind in shared_kinds:
            facts.append(f"Shared signal kind {kind} ({KIND_LABELS.get(kind, kind)})")
        if body.get("primary_entity_type") and body.get("primary_entity_type") == case.primary_entity_type:
            facts.append(f"Same primary entity type ({case.primary_entity_type})")
        if not shared_rules and not shared_kinds:
            continue
        hits.append(
            {
                "page_id": page.page_id,
                "slug": page.slug,
                "title": page.title,
                "source_case": body.get("source_case"),
                "decision": body.get("decision"),
                "why_it_matches": "Structured overlap on stored detector rules/kinds from the approved precedent.",
                "matching_facts": facts,
                "citation": f"prec:{page.page_id}",
            }
        )
    return hits


def proposal_for_case(session: Session, case_id: str) -> WikiProposal | None:
    return session.execute(
        select(WikiProposal)
        .where(WikiProposal.source_case_id == case_id)
        .order_by(WikiProposal.created_at.desc())
        .limit(1)
    ).scalar_one_or_none()


def label_for_case(session: Session, case_id: str) -> Label | None:
    return session.execute(
        select(Label).where(Label.case_id == case_id).order_by(Label.created_at.desc()).limit(1)
    ).scalar_one_or_none()


def proposal_for_decision(session: Session, decision_id: str) -> WikiProposal | None:
    return session.execute(
        select(WikiProposal).where(WikiProposal.decision_id == decision_id)
    ).scalar_one_or_none()
