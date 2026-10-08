"""Run the three detector layers on one extract. Shared by the pipeline and risk training."""

from __future__ import annotations

from dataclasses import dataclass

import networkx as nx
import pandas as pd

from claimshield.anomaly.peer import evaluate_anomalies
from claimshield.graph.build import build_graph, strong_component_map
from claimshield.graph.detect import evaluate_graph
from claimshield.rules.catalog import stamp_catalog
from claimshield.rules.engine import AlertDraft, evaluate_rules


@dataclass
class DetectorOutput:
    graph: nx.Graph
    strong: dict[str, str]
    alerts: list[AlertDraft]


def run_detectors(tables: dict[str, pd.DataFrame]) -> DetectorOutput:
    graph = build_graph(tables)
    strong = strong_component_map(graph)
    alerts = stamp_catalog(evaluate_rules(tables) + evaluate_anomalies(tables) + evaluate_graph(tables, graph, strong))
    return DetectorOutput(graph=graph, strong=strong, alerts=alerts)
