from __future__ import annotations

from datetime import UTC, datetime
from typing import Any

import pandas as pd
from sqlalchemy.orm import Session

from claimshield.anomaly.peer import evaluate_anomalies
from claimshield.audit.service import append_event
from claimshield.cases.builder import build_cases
from claimshield.core.config import Settings
from claimshield.core.ids import new_id
from claimshield.db.models import Alert, Batch, Case, PipelineRun, User
from claimshield.graph.build import build_graph, communities_for
from claimshield.ingest.service import persist_dataset
from claimshield.queue.knapsack import expected_value, knapsack_select
from claimshield.rules.engine import AlertDraft, evaluate_rules
from claimshield.synth.generator import generate


def discrete_hazard(case: dict[str, Any]) -> tuple[float, float, float]:
    base = min(0.9, 0.12 + 0.35 * float(case["p_confirm"]) + 0.04 * int(case["harm"]))
    f30 = round(base, 3)
    f60 = round(min(0.97, base + 0.14), 3)
    f90 = round(min(0.99, base + 0.24), 3)
    return f30, f60, f90


def detect(tables: dict[str, pd.DataFrame], *, horizon_days: int, recovery: float, harm_lambda: float, capacity_hours: float) -> dict[str, Any]:
    alerts = evaluate_rules(tables) + evaluate_anomalies(tables)
    graph = build_graph(tables)
    communities = communities_for(graph)
    cases = build_cases(alerts, tables, communities)
    for case in cases:
        case["ev"] = expected_value(
            case, horizon_days=horizon_days, recovery=recovery, harm_lambda=harm_lambda
        )
        case["f30"], case["f60"], case["f90"] = discrete_hazard(case)
    priority = [c for c in cases if c["harm"] >= 4]
    rest = [c for c in cases if c["harm"] < 4]
    used = sum(float(c["estimated_hours"]) for c in priority)
    remaining = max(0.5, float(capacity_hours) - used)
    selected_rest = knapsack_select(rest, capacity_hours=remaining)
    chosen = {c["case_id"] for c in priority} | {c["case_id"] for c in selected_rest}
    for case in cases:
        if case["harm"] >= 4:
            case["lane"] = "harm_priority"
        elif case["case_id"] in chosen:
            case["lane"] = "selected"
        elif case["evidence_strength"] < 0.4:
            case["lane"] = "needs_evidence"
        else:
            case["lane"] = "overflow"
    return {
        "alerts": alerts,
        "cases": cases,
        "graph_nodes": graph.number_of_nodes(),
        "graph_edges": graph.number_of_edges(),
        "selected": len(chosen),
    }


def persist_detection(
    session: Session,
    *,
    run_id: str,
    alerts: list[AlertDraft],
    cases: list[dict[str, Any]],
) -> None:
    case_for_alert: dict[int, str] = {}
    for case in cases:
        for alert in case["alerts"]:
            case_for_alert[id(alert)] = case["case_id"]
        session.add(
            Case(
                case_id=case["case_id"],
                run_id=run_id,
                status="open",
                lane=case["lane"],
                assignee_id=None,
                sla_due=None,
                primary_entity_id=case["primary_entity_id"],
                primary_entity_type=case["primary_entity_type"],
                harm=case["harm"],
                severity=case["severity"],
                members_affected=case["members_affected"],
                flagged_dollars=case["flagged_dollars"],
                evidence_strength=case["evidence_strength"],
                estimated_hours=case["estimated_hours"],
                p_confirm=case["p_confirm"],
                f30=case["f30"],
                f60=case["f60"],
                f90=case["f90"],
            )
        )
    for alert in alerts:
        session.add(
            Alert(
                alert_id=new_id("ALRT"),
                run_id=run_id,
                detector=alert.detector,
                rule_id=alert.rule_id,
                rule_version=alert.rule_version,
                entity_id=alert.entity_id,
                entity_type=alert.entity_type,
                line_ids=alert.line_ids,
                score=alert.score,
                evidence=alert.evidence,
                case_id=case_for_alert.get(id(alert)),
            )
        )
    session.flush()


def execute_run(
    session: Session,
    *,
    batch: Batch,
    user: User,
    tables: dict[str, pd.DataFrame],
    settings: Settings,
    horizon_days: int = 60,
    capacity_hours: float = 40.0,
    now: datetime | None = None,
) -> PipelineRun:
    instant = now or datetime.now(UTC)
    run = PipelineRun(
        run_id=new_id("RUN"),
        batch_id=batch.batch_id,
        horizon_days=horizon_days,
        status="running",
        summary={},
        created_at=instant,
        created_by=user.id,
    )
    session.add(run)
    session.flush()
    result = detect(
        tables,
        horizon_days=horizon_days,
        recovery=settings.default_recovery_rate,
        harm_lambda=250.0,
        capacity_hours=capacity_hours,
    )
    persist_detection(session, run_id=run.run_id, alerts=result["alerts"], cases=result["cases"])
    summary = {
        "n_alerts": len(result["alerts"]),
        "n_cases": len(result["cases"]),
        "n_selected": result["selected"],
        "graph_nodes": result["graph_nodes"],
        "graph_edges": result["graph_edges"],
        "capacity_hours": capacity_hours,
        "horizon_days": horizon_days,
        "lanes": _lane_counts(result["cases"]),
    }
    run.status = "completed"
    run.summary = summary
    append_event(
        session,
        actor_id=user.id,
        role=user.role,
        action="run.start",
        object_type="run",
        object_id=run.run_id,
        payload={"batch_id": batch.batch_id, "summary": summary},
        ts=instant,
    )
    session.flush()
    return run


def load_synthetic_batch(
    session: Session,
    *,
    user: User,
    settings: Settings,
    profile: str,
    seed: int,
    horizon_days: int = 60,
    capacity_hours: float = 40.0,
    run_now: bool = True,
) -> tuple[Batch, PipelineRun | None]:
    instant = datetime.now(UTC)
    dataset = generate(profile=profile, seed=seed)
    report = persist_dataset(session, dataset)
    batch = Batch(
        batch_id=report["batch_tag"],
        adapter="synthetic",
        status="loaded",
        profile=profile,
        seed=seed,
        load_report={
            "tables": report["tables"],
            "ground_truth_rows": report["ground_truth_rows"],
            "scheme_ids": report["scheme_ids"],
            "data_card": report["data_card"],
        },
        created_at=instant,
        created_by=user.id,
    )
    session.add(batch)
    session.flush()
    append_event(
        session,
        actor_id=user.id,
        role=user.role,
        action="batch.load",
        object_type="batch",
        object_id=batch.batch_id,
        payload={"profile": profile, "seed": seed, "adapter": "synthetic"},
        ts=instant,
    )
    run = None
    if run_now:
        run = execute_run(
            session,
            batch=batch,
            user=user,
            tables=dataset.tables,
            settings=settings,
            horizon_days=horizon_days,
            capacity_hours=capacity_hours,
            now=instant,
        )
    return batch, run


def _lane_counts(cases: list[dict[str, Any]]) -> dict[str, int]:
    counts: dict[str, int] = {}
    for case in cases:
        counts[case["lane"]] = counts.get(case["lane"], 0) + 1
    return counts
