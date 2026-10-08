from __future__ import annotations

from datetime import UTC, datetime, timedelta
from typing import Any

import pandas as pd
from sqlalchemy import select
from sqlalchemy.orm import Session

from claimshield.anomaly.peer import evaluate_anomalies
from claimshield.audit.service import append_event
from claimshield.cases.builder import build_cases
from claimshield.core.config import Settings
from claimshield.core.ids import new_id
from claimshield.db.models import Alert, Batch, Case, PipelineRun, User
from claimshield.graph.build import build_graph, strong_component_map
from claimshield.graph.detect import evaluate_graph
from claimshield.core.errors import NotFound
from claimshield.ingest.service import load_tables, persist_dataset
from claimshield.queue.knapsack import expected_value, knapsack_select
from claimshield.rules.catalog import stamp_catalog
from claimshield.rules.engine import AlertDraft, evaluate_rules
from claimshield.synth.generator import generate


def discrete_hazard(case: dict[str, Any]) -> tuple[float, float, float]:
    """Constant monthly hazard, discrete-time CDF at 1/2/3 months."""
    monthly = 0.05 + 0.28 * float(case["p_confirm"]) + 0.03 * int(case["harm"])
    monthly = min(0.65, max(0.02, monthly))
    case["monthly_hazard"] = round(monthly, 4)

    def cdf(months: int) -> float:
        return round(1.0 - (1.0 - monthly) ** months, 3)

    return cdf(1), cdf(2), cdf(3)


def assign_lanes(
    cases: list[dict[str, Any]],
    *,
    capacity_hours: float,
    harm_capacity_share: float,
    evidence_min: float,
) -> None:
    harm = [c for c in cases if c["harm"] >= 4]
    rest = [c for c in cases if c["harm"] < 4]
    for case in harm:
        case["lane"] = "harm_priority"
    harm_hours = sum(float(c["estimated_hours"]) for c in harm)
    reserved = min(harm_hours, max(0.0, float(capacity_hours) * harm_capacity_share))
    remaining = max(0.5, float(capacity_hours) - reserved)
    needs = [c for c in rest if c["evidence_strength"] < evidence_min]
    workable = [c for c in rest if c["evidence_strength"] >= evidence_min]
    for case in needs:
        case["lane"] = "needs_evidence"
    selected_rest = knapsack_select(workable, capacity_hours=remaining)
    chosen = {c["case_id"] for c in selected_rest}
    for case in workable:
        case["lane"] = "selected" if case["case_id"] in chosen else "overflow"


def detect(
    tables: dict[str, pd.DataFrame],
    *,
    horizon_days: int,
    recovery: float,
    harm_lambda: float,
    capacity_hours: float,
    harm_capacity_share: float = 0.35,
    evidence_min: float = 0.4,
) -> dict[str, Any]:
    graph = build_graph(tables)
    strong = strong_component_map(graph)
    alerts = stamp_catalog(
        evaluate_rules(tables)
        + evaluate_anomalies(tables)
        + evaluate_graph(tables, graph, strong)
    )
    cases = build_cases(alerts, tables, strong)
    for case in cases:
        case["ev"] = expected_value(
            case, horizon_days=horizon_days, recovery=recovery, harm_lambda=harm_lambda
        )
        case["f30"], case["f60"], case["f90"] = discrete_hazard(case)
    assign_lanes(
        cases,
        capacity_hours=capacity_hours,
        harm_capacity_share=harm_capacity_share,
        evidence_min=evidence_min,
    )
    selected = sum(1 for c in cases if c["lane"] in {"harm_priority", "selected"})
    return {
        "alerts": alerts,
        "cases": cases,
        "graph_nodes": graph.number_of_nodes(),
        "graph_edges": graph.number_of_edges(),
        "selected": selected,
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
                sla_due=case.get("sla_due"),
                primary_entity_id=case["primary_entity_id"],
                primary_entity_type=case["primary_entity_type"],
                entity_ids=case.get("entity_ids") or [case["primary_entity_id"]],
                harm=case["harm"],
                severity=case["severity"],
                members_affected=case["members_affected"],
                flagged_dollars=case["flagged_dollars"],
                evidence_strength=case["evidence_strength"],
                estimated_hours=case["estimated_hours"],
                p_confirm=case["p_confirm"],
                expected_value=float(case.get("ev") or 0.0),
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
        harm_lambda=settings.harm_lambda,
        capacity_hours=capacity_hours,
        harm_capacity_share=settings.harm_capacity_share,
        evidence_min=settings.evidence_strength_min,
    )
    sla_due = instant.date() + timedelta(days=int(settings.screening_days))
    for case in result["cases"]:
        case["sla_due"] = sla_due
    persist_detection(session, run_id=run.run_id, alerts=result["alerts"], cases=result["cases"])
    summary = {
        "n_alerts": len(result["alerts"]),
        "n_cases": len(result["cases"]),
        "n_selected": result["selected"],
        "graph_nodes": result["graph_nodes"],
        "graph_edges": result["graph_edges"],
        "capacity_hours": capacity_hours,
        "horizon_days": horizon_days,
        "screening_days": int(settings.screening_days),
        "harm_lambda": settings.harm_lambda,
        "recompute": False,
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


def latest_batch(session: Session) -> Batch | None:
    return session.execute(select(Batch).order_by(Batch.created_at.desc())).scalars().first()


def latest_run(session: Session) -> PipelineRun | None:
    return session.execute(
        select(PipelineRun).where(PipelineRun.status == "completed").order_by(PipelineRun.created_at.desc())
    ).scalars().first()


def tables_for_batch(session: Session, batch: Batch) -> dict[str, pd.DataFrame]:
    if batch.adapter == "synthetic" and batch.profile and batch.seed is not None:
        return generate(profile=batch.profile, seed=batch.seed).tables
    tables = load_tables(session)
    if tables.get("claim") is None or tables["claim"].empty:
        raise NotFound("no persisted extract to re-run")
    return tables


def recompute_run(
    session: Session,
    *,
    user: User,
    settings: Settings,
    batch: Batch | None = None,
    horizon_days: int = 60,
    capacity_hours: float = 40.0,
) -> PipelineRun:
    target = batch or latest_batch(session)
    if target is None:
        raise NotFound("no batch loaded")
    tables = tables_for_batch(session, target)
    run = execute_run(
        session,
        batch=target,
        user=user,
        tables=tables,
        settings=settings,
        horizon_days=horizon_days,
        capacity_hours=capacity_hours,
    )
    summary = dict(run.summary or {})
    summary["recompute"] = True
    summary["source_batch_id"] = target.batch_id
    run.summary = summary
    append_event(
        session,
        actor_id=user.id,
        role=user.role,
        action="run.recompute",
        object_type="run",
        object_id=run.run_id,
        payload={
            "batch_id": target.batch_id,
            "capacity_hours": capacity_hours,
            "horizon_days": horizon_days,
        },
    )
    session.flush()
    return run


def _lane_counts(cases: list[dict[str, Any]]) -> dict[str, int]:
    counts: dict[str, int] = {}
    for case in cases:
        counts[case["lane"]] = counts.get(case["lane"], 0) + 1
    return counts
