"""Case network: who is linked to the case's providers, how, and on what evidence.

Scope rules (so a one-provider case does not pull in most of the extract):

* Hop 0 is the case subjects (``case.entity_ids``). Billing, rendering and ordering providers,
  members and facilities on the case's flagged claim lines are added as in-case context.
* Hop 1 adds providers that share an owner, TIN, contact point or practice address with a
  subject, plus each subject's top-N referral partners by volume.
* Hop 2 (``hops=2``) follows only strong identity links (owner, TIN, contact) from hop-1
  providers that were themselves reached by an identity link. Address-only and referral-only
  neighbours are leaves.
* A shared address is a hub node (``address``) with ``located_at`` edges, not a clique.
"""

from __future__ import annotations

from collections import defaultdict
from dataclasses import dataclass, field
from typing import Any
from urllib.parse import quote

from sqlalchemy import select
from sqlalchemy.orm import Session

from claimshield.cases.builder import LINK_KINDS
from claimshield.cases.common import (
    alerts_for,
    audit_unmask,
    can_unmask,
    claim_rows,
    iso,
    line_ids_for,
    member_display,
    serialize_alert,
    serialize_lines,
)
from claimshield.cases.network_models import (
    EdgeEvidence,
    EdgeKind,
    NetworkEdge,
    NetworkLimits,
    NetworkNode,
    NetworkPack,
    ClaimVolume,
    EntitySummary,
    NodeDetail,
    NodeType,
    RelatedCase,
    SharedAttribute,
)
from claimshield.core.errors import NotFound
from claimshield.db.models import (
    Alert,
    Case,
    Claim,
    ClaimLine,
    ContactPoint,
    Facility,
    Location,
    Member,
    Owner,
    OwnershipLink,
    Provider,
    Referral,
    User,
)

DEFAULT_REFERRAL_TOP_N = 5
MAX_PROVIDERS = 40
MAX_MEMBERS = 25
EVIDENCE_ID_CAP = 50
ADDRESS_PREFIX = "addr:"

DIRECTED_KINDS: frozenset[str] = frozenset(
    {"rendered", "billed", "at_facility", "owns", "referral", "located_at", "prescribed", "dispensed"}
)
# Links inferred from a shared identifier rather than a recorded relationship.
INFERRED_KINDS: frozenset[str] = frozenset({"shared_tin", "shared_contact"})
# Ring alerts list the strong link kinds they rely on; map network edge kinds onto them.
RING_EDGE_KIND: dict[str, str] = {"owns": "shared_owner", "shared_tin": "shared_tin", "shared_contact": "shared_contact"}
EDGE_LABELS: dict[str, str] = {
    "prescribed": "prescribed high-MME opioid",
    "dispensed": "dispensed high-MME opioid",
    "rendered": "rendered flagged service",
    "billed": "billed flagged service",
    "at_facility": "service at facility",
    "owns": "owns",
    "referral": "referred",
    "located_at": "practice address",
    "shared_tin": "shared TIN",
    "shared_contact": "shared contact",
}
RX_EDGES: tuple[tuple[str, EdgeKind], ...] = (("prescriber_id", "prescribed"), ("pharmacy_id", "dispensed"))
CONTACT_LABELS: dict[str, str] = {"phone": "phone", "email": "email", "bank_token": "bank account"}


def mask_value(kind: str, value: str) -> str:
    """Show the identifier type and last four characters only."""
    tail = value[-4:] if len(value) >= 4 else value
    return f"{CONTACT_LABELS.get(kind, kind)} ••••{tail}"


def _cap(values: list[Any]) -> list[Any]:
    return values[:EVIDENCE_ID_CAP]


@dataclass
class _EdgeDraft:
    source: str
    target: str
    kind: EdgeKind
    count: int = 0
    line_ids: list[str] = field(default_factory=list)
    claim_ids: list[str] = field(default_factory=list)
    referral_ids: list[int] = field(default_factory=list)
    alert_ids: set[str] = field(default_factory=set)
    attribute: SharedAttribute | None = None
    ownership_pct: float | None = None
    dates: list[str] = field(default_factory=list)
    paid: float = 0.0


class _NetworkBuilder:
    def __init__(self, session: Session, case: Case, *, hops: int, referral_top_n: int, reveal: bool) -> None:
        self.session = session
        self.case = case
        self.hops = max(1, min(int(hops), 2))
        self.referral_top_n = max(1, int(referral_top_n))
        self.reveal = reveal
        self.alerts: list[Alert] = alerts_for(session, case.case_id)
        all_subjects = list(dict.fromkeys([case.primary_entity_id, *(case.entity_ids or [])]))
        # A member-level case (e.g. a multiple-prescriber opioid pattern) has a member subject;
        # provider expansion starts from provider subjects only.
        self.member_subjects: set[str] = {case.primary_entity_id} if case.primary_entity_type == "member" else set()
        self.subject_ids: list[str] = all_subjects
        self.subjects: list[str] = [s for s in all_subjects if s not in self.member_subjects]
        self.rx_providers: dict[str, int] = {}
        self.nodes: dict[str, NetworkNode] = {}
        self.drafts: dict[tuple[str, str, str], _EdgeDraft] = {}
        self.provider_rows: dict[str, Provider] = {}
        self.provider_hop: dict[str, int] = {}
        self.providers_dropped = 0
        self.members_total = 0
        self.referral_pairs: set[tuple[str, str]] = set()
        self.ownership: list[OwnershipLink] = []
        self.lines: list[ClaimLine] = []
        self.claims: dict[str, Claim] = {}
        self.alerts_by_line: dict[str, set[str]] = defaultdict(set)
        for alert in self.alerts:
            for lid in alert.line_ids or []:
                self.alerts_by_line[lid].add(alert.alert_id)

    # ------------------------------------------------------------------ build
    def build(self) -> NetworkPack:
        self._load_flagged_lines()
        self._expand_providers()
        self._add_provider_nodes()
        self._add_claim_context()
        self._add_rx_context()
        self._add_owners()
        self._add_addresses()
        self._add_shared_tins()
        self._add_shared_contacts()
        self._add_referrals()
        self._attribute_alerts()
        edges = self._finalize_edges()
        providers_shown = sum(1 for n in self.nodes.values() if n.type == "provider")
        members_shown = sum(1 for n in self.nodes.values() if n.type == "member")
        return NetworkPack(
            case_id=self.case.case_id,
            hops=self.hops,
            primary_entity_id=self.case.primary_entity_id,
            subject_ids=self.subject_ids,
            masked=not self.reveal,
            nodes=sorted(self.nodes.values(), key=lambda n: (n.hop, n.type, n.id)),
            edges=edges,
            limits=NetworkLimits(
                hops=self.hops,
                referral_top_n=self.referral_top_n,
                max_providers=MAX_PROVIDERS,
                max_members=MAX_MEMBERS,
                providers_shown=providers_shown,
                providers_dropped=self.providers_dropped,
                members_total=self.members_total,
                members_shown=members_shown,
            ),
        )

    # -------------------------------------------------------------- loading
    def _load_flagged_lines(self) -> None:
        lids = line_ids_for(self.alerts)
        if not lids:
            return
        self.lines = list(self.session.execute(select(ClaimLine).where(ClaimLine.line_id.in_(lids))).scalars())
        claim_ids = {ln.claim_id for ln in self.lines}
        self.claims = {
            c.claim_id: c for c in self.session.execute(select(Claim).where(Claim.claim_id.in_(claim_ids))).scalars()
        }

    def _claim_providers(self) -> set[str]:
        found: set[str] = set()
        for ln in self.lines:
            found.add(ln.rendering_provider_id)
            if ln.ordering_provider_id:
                found.add(ln.ordering_provider_id)
            claim = self.claims.get(ln.claim_id)
            if claim is not None:
                found.add(claim.billing_provider_id)
        return found

    def _providers(self, ids: set[str]) -> dict[str, Provider]:
        missing = ids - self.provider_rows.keys()
        if missing:
            for row in self.session.execute(select(Provider).where(Provider.provider_id.in_(missing))).scalars():
                self.provider_rows[row.provider_id] = row
        return {pid: self.provider_rows[pid] for pid in ids if pid in self.provider_rows}

    # ------------------------------------------------------------ expansion
    def _identity_neighbours(self, pids: set[str], *, include_address: bool) -> dict[str, str]:
        """Providers linked to ``pids`` and the strongest link kind that reached them."""
        rows = self._providers(pids)
        found: dict[str, str] = {}
        owner_ids = {
            lk.owner_id
            for lk in self.session.execute(select(OwnershipLink).where(OwnershipLink.provider_id.in_(pids))).scalars()
        }
        if owner_ids:
            stmt = select(OwnershipLink).where(OwnershipLink.owner_id.in_(owner_ids))
            for lk in self.session.execute(stmt).scalars():
                found.setdefault(lk.provider_id, "owner")
        tins = {p.tin_token for p in rows.values()}
        if tins:
            for p in self.session.execute(select(Provider).where(Provider.tin_token.in_(tins))).scalars():
                self.provider_rows[p.provider_id] = p
                found.setdefault(p.provider_id, "tin")
        values = {
            cp.value_hash
            for cp in self.session.execute(select(ContactPoint).where(ContactPoint.entity_id.in_(pids))).scalars()
        }
        if values:
            stmt_cp = select(ContactPoint).where(
                ContactPoint.value_hash.in_(values), ContactPoint.entity_type == "provider"
            )
            for cp in self.session.execute(stmt_cp).scalars():
                found.setdefault(cp.entity_id, "contact")
        if include_address:
            locs = {p.location_id for p in rows.values()}
            for p in self.session.execute(select(Provider).where(Provider.location_id.in_(locs))).scalars():
                self.provider_rows[p.provider_id] = p
                found.setdefault(p.provider_id, "address")
        for pid in pids:
            found.pop(pid, None)
        return found

    def _top_referral_partners(self) -> set[str]:
        subjects = set(self.subjects)
        stmt = select(Referral).where(Referral.referring_id.in_(subjects) | Referral.receiving_id.in_(subjects))
        volume: dict[tuple[str, str], int] = defaultdict(int)
        for ref in self.session.execute(stmt).scalars():
            volume[(ref.referring_id, ref.receiving_id)] += 1
        partners: set[str] = set()
        for subject in self.subjects:
            ranked = sorted(
                ((pair, n) for pair, n in volume.items() if subject in pair),
                key=lambda item: (-item[1], item[0]),
            )
            for pair, _n in ranked[: self.referral_top_n]:
                self.referral_pairs.add(pair)
                partners.update(pair)
        for pair in volume:
            if pair[0] in subjects and pair[1] in subjects:
                self.referral_pairs.add(pair)
        return partners - subjects

    def _expand_providers(self) -> None:
        hop: dict[str, int] = {pid: 0 for pid in self.subjects}
        weak: set[str] = set()
        for pid in self._claim_providers():
            hop.setdefault(pid, 1)
        for alert in self.alerts:
            evidence = alert.evidence or {}
            if evidence.get("kind") == "doctor_shopping":
                for pid in [*(evidence.get("prescriber_ids") or []), *(evidence.get("pharmacy_ids") or [])]:
                    self.rx_providers[str(pid)] = 1
                    hop.setdefault(str(pid), 1)
        frontier = set(self.subjects)
        for level in range(1, self.hops + 1):
            reached = self._identity_neighbours(frontier, include_address=level == 1)
            strong = {pid for pid, via in reached.items() if via != "address"}
            for pid, via in reached.items():
                if pid not in hop:
                    hop[pid] = level
                    if via == "address":
                        weak.add(pid)
            if level == 1:
                for pid in self._top_referral_partners():
                    if pid not in hop:
                        hop[pid] = 1
                        weak.add(pid)
            frontier = {pid for pid in strong if hop[pid] == level}
            if not frontier:
                break
        ranked = sorted(hop, key=lambda pid: (hop[pid], pid in weak, pid))
        keep = ranked[:MAX_PROVIDERS]
        self.providers_dropped = max(0, len(ranked) - len(keep))
        self.provider_hop = {pid: hop[pid] for pid in keep}
        self._providers(set(keep))

    # ---------------------------------------------------------------- nodes
    def _node(self, nid: str, ntype: NodeType, label: str, hop: int, **extra: Any) -> NetworkNode:
        node = self.nodes.get(nid)
        if node is None:
            node = NetworkNode(
                id=nid,
                type=ntype,
                label=label,
                hop=hop,
                detail_path=f"/api/v1/cases/{self.case.case_id}/network/nodes/{quote(nid, safe='')}",
                **extra,
            )
            self.nodes[nid] = node
        return node

    def _edge(self, source: str, target: str, kind: EdgeKind) -> _EdgeDraft:
        if kind not in DIRECTED_KINDS and target < source:
            source, target = target, source
        key = (source, target, kind)
        draft = self.drafts.get(key)
        if draft is None:
            draft = _EdgeDraft(source=source, target=target, kind=kind)
            self.drafts[key] = draft
        return draft

    def _add_provider_nodes(self) -> None:
        subjects = set(self.subjects)
        claim_providers = self._claim_providers()
        for pid, hop in self.provider_hop.items():
            row = self.provider_rows.get(pid)
            node = self._node(
                pid,
                "provider",
                row.name if row else pid,
                hop,
                specialty=row.specialty if row else None,
                is_subject=pid in subjects,
                in_case=pid in subjects or pid in claim_providers or pid in self.rx_providers,
            )
            if pid in subjects:
                node.harm = self.case.harm
                node.severity = self.case.severity
            if pid == self.case.primary_entity_id:
                node.primary = True
                node.risk = self.case.p_confirm

    def _add_claim_context(self) -> None:
        member_lines: dict[str, int] = defaultdict(int)
        for ln in self.lines:
            claim = self.claims.get(ln.claim_id)
            if claim is not None:
                member_lines[claim.member_id] += 1
        self.members_total = len(member_lines)
        keep_members = set(sorted(member_lines, key=lambda m: (-member_lines[m], m))[:MAX_MEMBERS])
        names: dict[str, str] = {}
        if keep_members:
            stmt = select(Member).where(Member.member_id.in_(keep_members))
            names = {m.member_id: m.name for m in self.session.execute(stmt).scalars()}
        keep_members |= self.member_subjects
        if keep_members - names.keys():
            stmt = select(Member).where(Member.member_id.in_(keep_members - names.keys()))
            names |= {m.member_id: m.name for m in self.session.execute(stmt).scalars()}
        for mid in sorted(keep_members):
            disp = member_display(mid, self.reveal, names.get(mid))
            subject = mid in self.member_subjects
            node = self._node(
                mid, "member", disp["display"], 0 if subject else 1, masked=disp["masked"], in_case=True
            )
            if subject:
                node.is_subject = True
                node.primary = mid == self.case.primary_entity_id
                node.risk = self.case.p_confirm if node.primary else None
                node.harm = self.case.harm
                node.severity = self.case.severity
        facility_ids = {c.facility_id for c in self.claims.values() if c.facility_id}
        if facility_ids:
            stmt_f = select(Facility).where(Facility.facility_id.in_(facility_ids))
            for fac in self.session.execute(stmt_f).scalars():
                self._node(fac.facility_id, "facility", fac.type, 1, facility_type=fac.type, in_case=True)
        for ln in self.lines:
            claim = self.claims.get(ln.claim_id)
            if claim is None or claim.member_id not in keep_members:
                continue
            # One edge per role: "rendered" only when the rendering provider is not the biller.
            pairs: list[tuple[str, str, EdgeKind]] = [(claim.billing_provider_id, claim.member_id, "billed")]
            if ln.rendering_provider_id != claim.billing_provider_id:
                pairs.append((ln.rendering_provider_id, claim.member_id, "rendered"))
            if claim.facility_id and claim.facility_id in self.nodes:
                pairs.append((ln.rendering_provider_id, claim.facility_id, "at_facility"))
            for source, target, kind in pairs:
                if source not in self.nodes or source == target:
                    continue
                draft = self._edge(source, target, kind)
                draft.count += 1
                draft.line_ids.append(ln.line_id)
                if ln.claim_id not in draft.claim_ids:
                    draft.claim_ids.append(ln.claim_id)
                draft.alert_ids |= self.alerts_by_line.get(ln.line_id, set())
                draft.paid += float(ln.paid or 0.0)
                draft.dates.append(iso(ln.dos_from) or "")

    def _add_rx_context(self) -> None:
        """Prescriber → member and pharmacy → member edges for member-level opioid patterns."""
        for alert in self.alerts:
            evidence = alert.evidence or {}
            member = str(evidence.get("member_id") or "")
            if evidence.get("kind") != "doctor_shopping" or member not in self.nodes:
                continue
            for fill in evidence.get("fills") or []:
                for key, kind in RX_EDGES:
                    source = str(fill.get(key) or "")
                    if source not in self.nodes:
                        continue
                    draft = self._edge(source, member, kind)
                    draft.count += 1
                    draft.alert_ids.add(alert.alert_id)
                    draft.dates.append(str(fill.get("fill_date") or ""))

    def _add_owners(self) -> None:
        pids = set(self.provider_hop)
        if not pids:
            return
        stmt = select(OwnershipLink).where(OwnershipLink.provider_id.in_(pids))
        self.ownership = list(self.session.execute(stmt).scalars())
        by_owner: dict[str, list[OwnershipLink]] = defaultdict(list)
        for lk in self.ownership:
            by_owner[lk.owner_id].append(lk)
        in_case = {n.id for n in self.nodes.values() if n.in_case}
        shown = {
            oid for oid, links in by_owner.items() if len(links) >= 2 or any(lk.provider_id in in_case for lk in links)
        }
        if not shown:
            return
        owners = {o.owner_id: o for o in self.session.execute(select(Owner).where(Owner.owner_id.in_(shown))).scalars()}
        for oid in sorted(shown):
            owner = owners.get(oid)
            hop = min(self.provider_hop.get(lk.provider_id, 2) for lk in by_owner[oid])
            self._node(oid, "owner", owner.name if owner else oid, hop, owner_kind=owner.kind if owner else None)
            for lk in by_owner[oid]:
                draft = self._edge(oid, lk.provider_id, "owns")
                draft.count = 1
                draft.ownership_pct = float(lk.pct)
                draft.dates.append(iso(lk.start) or "")

    def _add_addresses(self) -> None:
        by_loc: dict[str, list[str]] = defaultdict(list)
        for pid in self.provider_hop:
            row = self.provider_rows.get(pid)
            if row is not None:
                by_loc[row.location_id].append(pid)
        shared = {loc: pids for loc, pids in by_loc.items() if len(pids) >= 2}
        if not shared:
            return
        stmt = select(Location).where(Location.location_id.in_(shared))
        locations = {loc.location_id: loc for loc in self.session.execute(stmt).scalars()}
        for loc_id, pids in sorted(shared.items()):
            loc = locations.get(loc_id)
            label = f"{loc.address_norm}, {loc.zip}" if loc else loc_id
            nid = f"{ADDRESS_PREFIX}{loc_id}"
            self._node(nid, "address", label, min(self.provider_hop[p] for p in pids))
            for pid in pids:
                draft = self._edge(pid, nid, "located_at")
                draft.count = 1
                draft.attribute = SharedAttribute(kind="address", value_masked=label)

    def _add_shared_tins(self) -> None:
        by_tin: dict[str, list[str]] = defaultdict(list)
        for pid in self.provider_hop:
            row = self.provider_rows.get(pid)
            if row is not None:
                by_tin[row.tin_token].append(pid)
        for tin, pids in by_tin.items():
            for i, a in enumerate(sorted(pids)):
                for b in sorted(pids)[i + 1 :]:
                    draft = self._edge(a, b, "shared_tin")
                    draft.count = 1
                    draft.attribute = SharedAttribute(kind="tin", value_masked=mask_value("TIN", tin))

    def _add_shared_contacts(self) -> None:
        entity_ids = [n.id for n in self.nodes.values() if n.type in {"provider", "owner"}]
        if not entity_ids:
            return
        stmt = select(ContactPoint).where(ContactPoint.entity_id.in_(entity_ids))
        groups: dict[tuple[str, str], set[str]] = defaultdict(set)
        for cp in self.session.execute(stmt).scalars():
            groups[(cp.kind, cp.value_hash)].add(cp.entity_id)
        for (kind, value), ids in sorted(groups.items()):
            members = sorted(ids)
            for i, a in enumerate(members):
                for b in members[i + 1 :]:
                    draft = self._edge(a, b, "shared_contact")
                    draft.count += 1
                    draft.attribute = SharedAttribute(kind=kind, value_masked=mask_value(kind, value))

    def _add_referrals(self) -> None:
        if not self.referral_pairs:
            return
        referring = {pair[0] for pair in self.referral_pairs}
        stmt = select(Referral).where(Referral.referring_id.in_(referring)).order_by(Referral.date, Referral.id)
        for ref in self.session.execute(stmt).scalars():
            pair = (ref.referring_id, ref.receiving_id)
            if pair not in self.referral_pairs or pair[0] not in self.nodes or pair[1] not in self.nodes:
                continue
            draft = self._edge(pair[0], pair[1], "referral")
            draft.count += 1
            draft.referral_ids.append(ref.id)
            draft.dates.append(iso(ref.date) or "")

    # ------------------------------------------------------------- evidence
    def _alert_parties(self, alert: Alert) -> set[str]:
        evidence = alert.evidence or {}
        parties = {alert.entity_id}
        if str(evidence.get("kind") or "") in LINK_KINDS:
            parties |= {str(x) for x in evidence.get("peer_ids") or []}
        return parties

    def _attribute_alerts(self) -> None:
        line_parties: dict[str, set[str]] = defaultdict(set)
        line_paid: dict[str, float] = {}
        for ln in self.lines:
            claim = self.claims.get(ln.claim_id)
            ids = {ln.rendering_provider_id}
            if ln.ordering_provider_id:
                ids.add(ln.ordering_provider_id)
            if claim is not None:
                ids |= {claim.billing_provider_id, claim.member_id}
                if claim.facility_id:
                    ids.add(claim.facility_id)
            line_parties[ln.line_id] = ids
            line_paid[ln.line_id] = float(ln.paid or 0.0)
        owned_by: dict[str, set[str]] = defaultdict(set)
        for lk in self.ownership:
            owned_by[lk.owner_id].add(lk.provider_id)
        rule_of = {a.alert_id: a.rule_id or a.detector for a in self.alerts}
        for alert in self.alerts:
            evidence = alert.evidence or {}
            touched = set(self._alert_parties(alert))
            for lid in alert.line_ids or []:
                touched |= line_parties.get(lid, set())
            member_refs = [evidence.get("member_id"), *(evidence.get("member_ids") or [])]
            touched |= {str(m) for m in member_refs if m}
            if evidence.get("owner_id"):
                touched.add(str(evidence["owner_id"]))
            if "shared_owner" in (evidence.get("edge_kinds") or []):
                ring = {str(x) for x in evidence.get("peer_ids") or []}
                touched |= {oid for oid, pids in owned_by.items() if len(pids & ring) >= 2}
            for nid in touched:
                node = self.nodes.get(nid)
                if node is not None and alert.alert_id not in node.alert_ids:
                    node.alert_ids.append(alert.alert_id)
        for node in self.nodes.values():
            node.rule_ids = sorted({rule_of[a] for a in node.alert_ids})
            lids = [lid for lid, ids in line_parties.items() if node.id in ids]
            node.n_flagged_lines = len(lids)
            node.flagged_paid = round(sum(line_paid[lid] for lid in lids), 2)
            if node.alert_ids and node.type in {"owner", "address"}:
                node.in_case = True
        self._attribute_structural_edges()

    def _attribute_structural_edges(self) -> None:
        for alert in self.alerts:
            evidence = alert.evidence or {}
            kind = str(evidence.get("kind") or "")
            ring = {str(x) for x in evidence.get("peer_ids") or []}
            edge_kinds = set(evidence.get("edge_kinds") or [])
            for draft in self.drafts.values():
                if kind == "identity_ring" and RING_EDGE_KIND.get(draft.kind) in edge_kinds:
                    ends = {draft.source, draft.target}
                    if (draft.kind == "owns" and draft.target in ring) or ends <= ring:
                        draft.alert_ids.add(alert.alert_id)
                elif kind == "excluded_owner" and draft.kind == "owns" and draft.source == evidence.get("owner_id"):
                    draft.alert_ids.add(alert.alert_id)
                elif (
                    kind == "referral_monopoly"
                    and draft.kind == "referral"
                    and draft.target == alert.entity_id
                    and draft.source == evidence.get("top_referrer")
                ):
                    draft.alert_ids.add(alert.alert_id)

    def _finalize_edges(self) -> list[NetworkEdge]:
        rule_of = {a.alert_id: a.rule_id or a.detector for a in self.alerts}
        max_count: dict[str, int] = defaultdict(int)
        for draft in self.drafts.values():
            max_count[draft.kind] = max(max_count[draft.kind], draft.count)
        edges: list[NetworkEdge] = []
        for draft in sorted(self.drafts.values(), key=lambda d: (d.kind, d.source, d.target)):
            if draft.source not in self.nodes or draft.target not in self.nodes:
                continue
            dates = sorted(d for d in draft.dates if d)
            source_node, target_node = self.nodes[draft.source], self.nodes[draft.target]
            alert_ids = sorted(draft.alert_ids)
            claim_ids, line_ids = _cap(draft.claim_ids), _cap(draft.line_ids)
            directed = draft.kind in DIRECTED_KINDS
            edges.append(
                NetworkEdge(
                    id=f"{draft.kind}:{draft.source}:{draft.target}",
                    source=draft.source,
                    target=draft.target,
                    kind=draft.kind,
                    directed=directed,
                    direction="out" if directed else "none",
                    inferred=draft.kind in INFERRED_KINDS,
                    evidence_ids=_cap(
                        [f"alert:{a}" for a in alert_ids]
                        + [f"claim:{c}" for c in claim_ids]
                        + [f"line:{ln}" for ln in line_ids]
                    ),
                    count=draft.count,
                    weight=round(draft.count / max(1, max_count[draft.kind]), 4),
                    label=_edge_label(draft),
                    in_case=bool(alert_ids) or (source_node.in_case and target_node.in_case),
                    evidence=EdgeEvidence(
                        alert_ids=alert_ids,
                        rule_ids=sorted({rule_of[a] for a in alert_ids}),
                        claim_ids=claim_ids,
                        line_ids=line_ids,
                        referral_ids=_cap(draft.referral_ids),
                        attribute=draft.attribute,
                        ownership_pct=draft.ownership_pct,
                        first_date=dates[0] if dates else None,
                        last_date=dates[-1] if dates else None,
                        paid=round(draft.paid, 2) if draft.line_ids else None,
                    ),
                )
            )
        return edges


def _edge_label(draft: _EdgeDraft) -> str:
    base = EDGE_LABELS.get(draft.kind, draft.kind)
    if draft.kind == "referral":
        return f"{base} ×{draft.count}"
    if draft.kind == "owns" and draft.ownership_pct is not None:
        return f"{base} {draft.ownership_pct:.0f}%"
    if draft.kind in {"rendered", "billed"}:
        return f"{base} ×{draft.count}"
    if draft.attribute is not None and draft.kind != "located_at":
        return f"{base} ({draft.attribute.value_masked})"
    return base


def network_pack(
    session: Session,
    case: Case,
    user: User,
    *,
    hops: int = 2,
    unmask: bool = False,
    referral_top_n: int = DEFAULT_REFERRAL_TOP_N,
) -> NetworkPack:
    reveal = audit_unmask(session, user=user, case=case, surface="network", unmask=unmask)
    return _NetworkBuilder(session, case, hops=hops, referral_top_n=referral_top_n, reveal=reveal).build()


def node_detail(
    session: Session,
    case: Case,
    user: User,
    node_id: str,
    *,
    unmask: bool = False,
    referral_top_n: int = DEFAULT_REFERRAL_TOP_N,
) -> NodeDetail:
    """Findings and flagged claim lines for one node of the case network (2-hop scope)."""
    reveal = audit_unmask(session, user=user, case=case, surface="network_node", unmask=unmask)
    builder = _NetworkBuilder(session, case, hops=2, referral_top_n=referral_top_n, reveal=reveal)
    pack = builder.build()
    node = next((n for n in pack.nodes if n.id == node_id), None)
    if node is None:
        raise NotFound("node is not in this case network")
    connections = [e for e in pack.edges if node_id in (e.source, e.target)]
    related = _related_ids(node, connections)
    rows = [row for row in claim_rows(session, builder.alerts, reveal=reveal) if _row_touches(row, node, related)]
    alerts = [serialize_alert(a) for a in builder.alerts if a.alert_id in set(node.alert_ids)]
    return NodeDetail(
        case_id=case.case_id,
        node=node,
        profile=_profile(builder, node),
        alerts=alerts,
        claim_lines=rows,
        connections=connections,
    )


ENTITY_SAMPLE_LINES = 10


def entity_summary(session: Session, case: Case, user: User, entity_id: str, *, unmask: bool = False) -> EntitySummary:
    """Claims on file, run-wide findings and cases for any node of the case network.

    The node must be inside the case's 2-hop network, so this cannot be used to browse
    arbitrary providers or members. Owners and addresses stand for the providers they connect.
    """
    detail = node_detail(session, case, user, entity_id, unmask=unmask)
    reveal = unmask and can_unmask(user)  # node_detail has already written the unmask audit event
    node = detail.node
    related = _related_ids(node, detail.connections)
    stmt = select(ClaimLine).join(Claim, Claim.claim_id == ClaimLine.claim_id)
    if node.type == "member":
        stmt = stmt.where(Claim.member_id == node.id)
    elif node.type == "facility":
        stmt = stmt.where(Claim.facility_id == node.id)
    else:
        stmt = stmt.where(
            Claim.billing_provider_id.in_(related)
            | ClaimLine.rendering_provider_id.in_(related)
            | ClaimLine.ordering_provider_id.in_(related)
        )
    lines = list(session.execute(stmt).scalars().all())
    dates = sorted(iso(ln.dos_from) or "" for ln in lines)
    recent = sorted(lines, key=lambda ln: (iso(ln.dos_from) or "", ln.line_id), reverse=True)[:ENTITY_SAMPLE_LINES]
    names = related | {node.id}
    run_alerts = list(session.execute(select(Alert).where(Alert.run_id == case.run_id)).scalars().all())
    in_node = set(node.alert_ids)
    alerts = [serialize_alert(a) for a in run_alerts if a.alert_id in in_node or _alert_names(a, names)]
    run_cases = session.execute(select(Case).where(Case.run_id == case.run_id)).scalars().all()
    cases = [
        RelatedCase(
            case_id=c.case_id,
            status=c.status,
            lane=c.lane,
            primary_entity_id=c.primary_entity_id,
            is_primary=c.primary_entity_id in names,
        )
        for c in run_cases
        if c.primary_entity_id in names or names & set(c.entity_ids or [])
    ]
    return EntitySummary(
        entity_id=node.id,
        case_id=case.case_id,
        node=node,
        profile=detail.profile,
        claims=ClaimVolume(
            n_lines=len(lines),
            paid=round(sum(float(ln.paid or 0.0) for ln in lines), 2),
            first_dos=dates[0] if dates else None,
            last_dos=dates[-1] if dates else None,
            sample=serialize_lines(session, recent, reveal=reveal),
        ),
        alerts=alerts,
        cases=cases,
        case_claim_lines=detail.claim_lines,
        connections=detail.connections,
    )


def _alert_names(alert: Alert, names: set[str]) -> bool:
    evidence = alert.evidence or {}
    named = {alert.entity_id, str(evidence.get("member_id") or ""), str(evidence.get("owner_id") or "")}
    for key in ("peer_ids", "member_ids"):
        named |= {str(v) for v in evidence.get(key) or []}
    return bool(named & names)


def network_edge(session: Session, case: Case, user: User, edge_id: str) -> NetworkEdge:
    """One edge of the case network (masked view), for ``edge:`` evidence citations."""
    pack = _NetworkBuilder(session, case, hops=2, referral_top_n=DEFAULT_REFERRAL_TOP_N, reveal=False).build()
    edge = next((e for e in pack.edges if e.id == edge_id), None)
    if edge is None:
        raise NotFound("edge is not in this case network")
    return edge


def _related_ids(node: NetworkNode, connections: list[NetworkEdge]) -> set[str]:
    """Owners and addresses stand for the providers they connect."""
    if node.type not in {"owner", "address"}:
        return {node.id}
    kind = "owns" if node.type == "owner" else "located_at"
    return {e.target if e.source == node.id else e.source for e in connections if e.kind == kind}


def _row_touches(row: dict[str, Any], node: NetworkNode, related: set[str]) -> bool:
    if node.type == "member":
        return bool(row["member"]["member_id"] == node.id)
    if node.type == "facility":
        return bool(row["facility_id"] == node.id)
    providers = {row["rendering_provider_id"], row["billing_provider_id"], row["ordering_provider_id"]}
    return bool(providers & related)


def _profile(builder: _NetworkBuilder, node: NetworkNode) -> dict[str, object]:
    if node.type == "provider":
        row = builder.provider_rows.get(node.id)
        if row is None:
            return {"provider_id": node.id}
        return {
            "provider_id": row.provider_id,
            "name": row.name,
            "npi_syn": row.npi_syn,
            "kind": row.kind,
            "specialty": row.specialty,
            "service_line": row.service_line,
            "enroll_date": iso(row.enroll_date),
            "rural": row.rural,
            "sole_community": row.sole_community,
        }
    if node.type == "owner":
        owner = builder.session.get(Owner, node.id)
        owned = sorted({lk.provider_id for lk in builder.ownership if lk.owner_id == node.id})
        return {"owner_id": node.id, "name": node.label, "kind": owner.kind if owner else None, "providers": owned}
    if node.type == "address":
        at = sorted(e.source for e in builder.drafts.values() if e.kind == "located_at" and e.target == node.id)
        return {"location_id": node.id.removeprefix(ADDRESS_PREFIX), "address": node.label, "providers": at}
    if node.type == "facility":
        return {"facility_id": node.id, "type": node.facility_type}
    return {"member": node.label, "masked": node.masked}
