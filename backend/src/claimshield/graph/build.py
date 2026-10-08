from __future__ import annotations

from collections import defaultdict

import networkx as nx
import pandas as pd


def build_graph(tables: dict[str, pd.DataFrame]) -> nx.Graph:
    graph = nx.Graph()
    providers = tables["provider"]
    for _, row in providers.iterrows():
        graph.add_node(row.provider_id, kind="provider", location_id=row.location_id, tin=row.tin_token)
    for loc_id, grp in providers.groupby("location_id"):
        ids = grp["provider_id"].tolist()
        for i, a in enumerate(ids):
            for b in ids[i + 1 :]:
                graph.add_edge(a, b, kind="shared_location")
    for tin, grp in providers.groupby("tin_token"):
        ids = grp["provider_id"].tolist()
        for i, a in enumerate(ids):
            for b in ids[i + 1 :]:
                graph.add_edge(a, b, kind="shared_tin")
    links = tables.get("ownership_link")
    if links is not None and not links.empty:
        by_owner: dict[str, list[str]] = defaultdict(list)
        for _, row in links.iterrows():
            by_owner[row.owner_id].append(row.provider_id)
        for pids in by_owner.values():
            for i, a in enumerate(pids):
                for b in pids[i + 1 :]:
                    if graph.has_node(a) and graph.has_node(b):
                        graph.add_edge(a, b, kind="shared_owner")
    contacts = tables.get("contact_point")
    if contacts is not None and not contacts.empty:
        for _, grp in contacts.groupby(["kind", "value_hash"]):
            ids = [e for e in grp["entity_id"].tolist() if graph.has_node(e)]
            for i, a in enumerate(ids):
                for b in ids[i + 1 :]:
                    graph.add_edge(a, b, kind="shared_contact")
    refs = tables.get("referral")
    if refs is not None and not refs.empty:
        for _, row in refs.iterrows():
            if graph.has_node(row.referring_id) and graph.has_node(row.receiving_id):
                graph.add_edge(row.referring_id, row.receiving_id, kind="referral")
    return graph


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
