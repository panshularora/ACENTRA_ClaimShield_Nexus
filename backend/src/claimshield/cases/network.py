"""Case network: providers, members, facilities and owners around a case."""

from __future__ import annotations

from typing import Any

from sqlalchemy import select
from sqlalchemy.orm import Session

from claimshield.cases.common import alerts_for, audit_unmask, line_ids_for, member_display
from claimshield.db.models import (
    Case,
    Claim,
    ClaimLine,
    Facility,
    Member,
    Owner,
    OwnershipLink,
    Provider,
    Referral,
    User,
)


def network_pack(session: Session, case: Case, user: User, *, hops: int = 2, unmask: bool = False) -> dict[str, Any]:
    hops = max(1, min(int(hops), 2))
    alerts = alerts_for(session, case.case_id)
    lids = line_ids_for(alerts)
    reveal = audit_unmask(session, user=user, case=case, surface="network", unmask=unmask)
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
    for mid in seed_members:
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
        linked_members: list[str] = []
        seen_members: set[str] = set()
        for edge in edges:
            for end in (edge["source"], edge["target"]):
                node = nodes.get(end)
                if not node or node["type"] != "member" or end in seen_members:
                    continue
                other = edge["target"] if edge["source"] == end else edge["source"]
                if other in keep:
                    seen_members.add(end)
                    linked_members.append(end)
        keep.update(linked_members[:20])
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

