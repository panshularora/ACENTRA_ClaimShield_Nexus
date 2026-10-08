"""Graph detectors: identity rings, referral concentration, excluded owners."""

from __future__ import annotations

from collections import defaultdict

import networkx as nx
import pandas as pd

from claimshield.graph.build import STRONG_EDGE_KINDS
from claimshield.rules import leie
from claimshield.rules.engine import AlertDraft


def evaluate_graph(
    tables: dict[str, pd.DataFrame],
    graph: nx.Graph,
    strong: dict[str, str],
) -> list[AlertDraft]:
    alerts: list[AlertDraft] = []
    alerts.extend(_identity_rings(tables, graph, strong))
    alerts.extend(_referral_concentration(tables))
    alerts.extend(_excluded_owner(tables))
    return alerts


def _lines_for_providers(tables: dict[str, pd.DataFrame], provider_ids: list[str]) -> pd.DataFrame:
    claims = tables["claim"][["claim_id", "billing_provider_id", "member_id"]]
    lines = tables["claim_line"].merge(claims, on="claim_id")
    return lines[lines.billing_provider_id.astype(str).isin(provider_ids)]


def _identity_rings(
    tables: dict[str, pd.DataFrame],
    graph: nx.Graph,
    strong: dict[str, str],
) -> list[AlertDraft]:
    by_ring: dict[str, list[str]] = defaultdict(list)
    for pid, rid in strong.items():
        by_ring[rid].append(pid)
    pagerank = nx.pagerank(graph) if graph.number_of_nodes() else {}
    providers = tables["provider"].set_index("provider_id")
    out: list[AlertDraft] = []
    for ring_id, pids in by_ring.items():
        if len(pids) < 2:
            continue
        kinds: set[str] = set()
        pid_set = set(pids)
        for u, v, data in graph.edges(pids, data=True):
            if u not in pid_set or v not in pid_set:
                continue
            edge_kinds = data.get("kinds")
            if isinstance(edge_kinds, set):
                kinds |= edge_kinds & STRONG_EDGE_KINDS
            elif data.get("kind") in STRONG_EDGE_KINDS:
                kinds.add(data.get("kind"))
        kinds_list = sorted(kinds)
        hit = _lines_for_providers(tables, pids)
        leader = max(pids, key=lambda p: pagerank.get(p, 0.0))
        enroll = []
        for pid in pids:
            if pid in providers.index:
                enroll.append(str(providers.loc[pid].enroll_date))
        out.append(
            AlertDraft(
                detector="graph",
                rule_id="G-RING-001",
                rule_version=1,
                entity_id=str(leader),
                entity_type="provider",
                line_ids=hit["line_id"].tolist()[:40] if not hit.empty else [],
                score=min(1.0, 0.45 + 0.12 * len(pids) + 0.08 * len(kinds)),
                related_entity_ids=[p for p in pids if p != leader],
                evidence={
                    "kind": "identity_ring",
                    "ring_id": ring_id,
                    "n_providers": len(pids),
                    "peer_ids": pids,
                    "edge_kinds": kinds_list,
                    "enroll_dates": enroll[:8],
                    "n_claims": int(hit["claim_id"].nunique()) if not hit.empty else 0,
                    "pagerank": round(float(pagerank.get(leader, 0.0)), 4),
                },
            )
        )
    return out


def _referral_concentration(tables: dict[str, pd.DataFrame]) -> list[AlertDraft]:
    refs = tables.get("referral")
    if refs is None or refs.empty:
        return []
    out: list[AlertDraft] = []
    for recv, grp in refs.groupby("receiving_id"):
        if len(grp) < 15:
            continue
        shares = grp.groupby("referring_id").size()
        total = float(shares.sum())
        top_share = float(shares.max() / total)
        hhi = float(((shares / total) ** 2).sum())
        if hhi < 0.45 and top_share < 0.65:
            continue
        top_ref = str(shares.idxmax())
        hit = _lines_for_providers(tables, [str(recv)])
        out.append(
            AlertDraft(
                detector="graph",
                rule_id="G-REF-001",
                rule_version=1,
                entity_id=str(recv),
                entity_type="provider",
                line_ids=hit["line_id"].tolist()[:40] if not hit.empty else [],
                score=round(min(1.0, 0.4 + 0.5 * top_share), 3),
                related_entity_ids=[top_ref],
                evidence={
                    "kind": "referral_monopoly",
                    "n_referrals": int(len(grp)),
                    "hhi": round(hhi, 3),
                    "top_share": round(top_share, 3),
                    "peer_ids": [top_ref],
                    "top_referrer": top_ref,
                },
            )
        )
    return out


def _owner_addresses(tables: dict[str, pd.DataFrame], provider_ids: list[str]) -> list[str]:
    """Practice addresses of the providers an owner holds (the owner table has no address)."""
    locations = tables.get("location")
    providers = tables["provider"]
    if locations is None or locations.empty or "location_id" not in providers:
        return []
    loc_ids = set(providers[providers.provider_id.astype(str).isin(provider_ids)]["location_id"].astype(str))
    return locations[locations.location_id.astype(str).isin(loc_ids)]["address_norm"].astype(str).tolist()


def _excluded_owner(tables: dict[str, pd.DataFrame]) -> list[AlertDraft]:
    """An owner is an excluded person: name, date of birth and address must all agree."""
    owners = tables.get("owner")
    excl = tables.get("exclusion_record")
    links = tables.get("ownership_link")
    if owners is None or excl is None or links is None or owners.empty or excl.empty or links.empty:
        return []
    records = excl.to_dict("records")
    out: list[AlertDraft] = []
    for owner in owners.itertuples(index=False):
        candidates = [r for r in records if leie.names_agree(owner.name, r)]
        candidates = [r for r in candidates if leie.same_date(getattr(owner, "dob", None), r.get("dob"))]
        if not candidates:
            continue
        pids = links[links.owner_id == owner.owner_id]["provider_id"].astype(str).tolist()
        if not pids:
            continue
        addresses = _owner_addresses(tables, pids)
        record = next(
            (r for r in candidates if any(leie.addresses_agree(r.get("address"), a) for a in addresses)),
            None,
        )
        if record is None:
            continue
        hit = _lines_for_providers(tables, pids)
        if not hit.empty:
            hit = hit[leie.exclusion_window_mask(hit["dos_from"], record)]
        out.append(
            AlertDraft(
                detector="graph",
                rule_id="G-OWN-001",
                rule_version=1,
                entity_id=str(pids[0]),
                entity_type="provider",
                line_ids=hit["line_id"].tolist()[:40] if not hit.empty else [],
                score=1.0,
                related_entity_ids=pids[1:],
                evidence={
                    "kind": "excluded_owner",
                    "owner_id": owner.owner_id,
                    "owner_name": owner.name,
                    "peer_ids": pids,
                    "excl_id": record.get("excl_id"),
                    "excl_date": leie.iso_date(record.get("excl_date")),
                    "match": "name_dob_address",
                },
            )
        )
    return out
