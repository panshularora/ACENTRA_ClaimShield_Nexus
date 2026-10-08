from __future__ import annotations

from collections import defaultdict
from typing import Any

import networkx as nx
import pandas as pd


def _link(graph: nx.Graph, a: str, b: str, kind: str) -> None:
    if a == b or not graph.has_node(a) or not graph.has_node(b):
        return
    if graph.has_edge(a, b):
        kinds = graph[a][b].get("kinds")
        if not isinstance(kinds, set):
            existing = graph[a][b].get("kind")
            kinds = {existing} if existing else set()
        kinds.add(kind)
        graph[a][b]["kinds"] = kinds
        graph[a][b]["kind"] = kind
        return
    graph.add_edge(a, b, kind=kind, kinds={kind})


def build_graph(tables: dict[str, pd.DataFrame]) -> nx.Graph:
    graph = nx.Graph()
    providers = tables["provider"]
    for _, row in providers.iterrows():
        graph.add_node(row.provider_id, kind="provider", location_id=row.location_id, tin=row.tin_token)
    for _, grp in providers.groupby("location_id"):
        ids = grp["provider_id"].tolist()
        for i, a in enumerate(ids):
            for b in ids[i + 1 :]:
                _link(graph, a, b, "shared_location")
    for _, grp in providers.groupby("tin_token"):
        ids = grp["provider_id"].tolist()
        for i, a in enumerate(ids):
            for b in ids[i + 1 :]:
                _link(graph, a, b, "shared_tin")
    links = tables.get("ownership_link")
    if links is not None and not links.empty:
        by_owner: dict[str, list[str]] = defaultdict(list)
        for _, row in links.iterrows():
            by_owner[row.owner_id].append(row.provider_id)
        for pids in by_owner.values():
            for i, a in enumerate(pids):
                for b in pids[i + 1 :]:
                    _link(graph, a, b, "shared_owner")
    contacts = tables.get("contact_point")
    if contacts is not None and not contacts.empty:
        for _, grp in contacts.groupby(["kind", "value_hash"]):
            ids = [e for e in grp["entity_id"].tolist() if graph.has_node(e)]
            for i, a in enumerate(ids):
                for b in ids[i + 1 :]:
                    _link(graph, a, b, "shared_contact")
    refs = tables.get("referral")
    if refs is not None and not refs.empty:
        for _, row in refs.iterrows():
            _link(graph, row.referring_id, row.receiving_id, "referral")
    return graph


STRONG_EDGE_KINDS = frozenset({"shared_owner", "shared_tin", "shared_contact"})


def communities_for(graph: nx.Graph) -> dict[str, int]:
    if graph.number_of_nodes() == 0:
        return {}
    try:
        parts = nx.community.leiden_communities(graph, seed=7)
    except Exception:
        parts = nx.community.louvain_communities(graph, seed=7)
    mapping: dict[str, int] = {}
    for i, community in enumerate(parts):
        for node in community:
            mapping[str(node)] = i
    return mapping


def strong_component_map(graph: nx.Graph) -> dict[str, str]:
    """Components linked by owner, TIN, or shared contact — not shared location."""
    if graph.number_of_edges() == 0:
        return {}

    def edge_kinds(data: dict[str, Any]) -> set[str]:
        kinds = data.get("kinds")
        if isinstance(kinds, set):
            return kinds
        kind = data.get("kind")
        return {kind} if kind else set()

    strong_edges = [(u, v) for u, v, data in graph.edges(data=True) if edge_kinds(data) & STRONG_EDGE_KINDS]
    if not strong_edges:
        return {}
    sub = graph.edge_subgraph(strong_edges).copy()
    mapping: dict[str, str] = {}
    for i, comp in enumerate(nx.connected_components(sub)):
        if len(comp) < 2:
            continue
        kinds: set[str] = set()
        for u, v in sub.edges(comp):
            kinds |= edge_kinds(sub.edges[u, v])
        kinds &= STRONG_EDGE_KINDS
        if len(kinds) < 2:
            continue
        cid = f"ring:{i}"
        for node in comp:
            mapping[str(node)] = cid
    return mapping
