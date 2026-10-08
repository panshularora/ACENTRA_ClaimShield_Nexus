from __future__ import annotations

from datetime import UTC, datetime, timedelta
from typing import Any

import pandas as pd
from sqlalchemy import select
from sqlalchemy.orm import Session

from claimshield.audit.service import append_event
from claimshield.cases.builder import build_cases
from claimshield.core.config import Settings
from claimshield.core.errors import NotFound
from claimshield.core.ids import new_id
from claimshield.db.models import Alert, Batch, Case, CaseRisk, PipelineRun, User
from claimshield.ingest.service import load_tables, persist_dataset
from claimshield.pipeline.detectors import run_detectors
from claimshield.queue.knapsack import expected_value, knapsack_select
from claimshield.queue.rank import attach_rank_factors, ranking_policy
from claimshield.risk.artifact import RiskArtifact, default_path, load_artifact
from claimshield.risk.scoring import score_cases
from claimshield.rules.engine import AlertDraft
from claimshield.synth.generator import Dataset, generate


def is_priority_override(case: dict[str, Any]) -> bool:
    """Beneficiary harm 4, or a program-integrity override (excluded party, services after death)."""
    return int(case["harm"]) >= 4 or bool(case.get("priority_override"))


def assign_lanes(
    cases: list[dict[str, Any]],
    *,
    capacity_hours: float,
    harm_capacity_share: float,
    evidence_min: float,
    max_slots: int = 20,
) -> dict[str, Any]:
    """Fill the investigator hours: override cases first, then the knapsack on what is left.

    Override hours count against capacity. When they alone exceed it, nothing else is selected
    and the shortfall is reported, so the queue never silently commits more hours than exist.
    """
    override = [c for c in cases if is_priority_override(c)]
    rest = [c for c in cases if not is_priority_override(c)]
    for case in override:
        case["lane"] = "harm_priority"
    capacity = max(0.0, float(capacity_hours))
    override_hours = sum(float(c["estimated_hours"]) for c in override)
    remaining = max(0.0, capacity - override_hours)
    needs = [c for c in rest if c["evidence_strength"] < evidence_min]
    workable = [c for c in rest if c["evidence_strength"] >= evidence_min]
    for case in needs:
        case["lane"] = "needs_evidence"
    selected_rest = knapsack_select(workable, capacity_hours=remaining, value_key="composite")
    chosen = {c["case_id"] for c in selected_rest}
    for case in workable:
        case["lane"] = "selected" if case["case_id"] in chosen else "overflow"
    _apply_slot_cap(cases, max_slots=max_slots)
    selected_hours = sum(float(c["estimated_hours"]) for c in cases if c["lane"] == "selected")
    used = override_hours + selected_hours
    return {
        "capacity_hours": round(capacity, 1),
        "priority_override_hours": round(override_hours, 1),
        "selected_hours": round(selected_hours, 1),
        "capacity_used_hours": round(used, 1),
        "over_capacity_hours": round(max(0.0, used - capacity), 1),
        "override_share": round(override_hours / capacity, 3) if capacity else None,
        "override_share_warning": bool(capacity) and override_hours > harm_capacity_share * capacity,
        "needs_evidence_hours": round(sum(float(c["estimated_hours"]) for c in needs), 1),
    }


def _apply_slot_cap(cases: list[dict[str, Any]], *, max_slots: int) -> None:
    """Keep harm-priority cases; trim selected so today's recommended set fits max_slots."""
    cap = max(1, int(max_slots))
    harm = [c for c in cases if c["lane"] == "harm_priority"]
    selected = [c for c in cases if c["lane"] == "selected"]
    leftover = cap - len(harm)
    if leftover >= len(selected):
        return
    if leftover <= 0:
        for case in selected:
            case["lane"] = "overflow"
        return
    ranked = sorted(selected, key=lambda c: float(c.get("composite") or 0.0), reverse=True)
    keep = {c["case_id"] for c in ranked[:leftover]}
    for case in selected:
        if case["case_id"] not in keep:
            case["lane"] = "overflow"


def detect(
    tables: dict[str, pd.DataFrame],
    *,
    horizon_days: int,
    recovery: float,
    capacity_hours: float,
    harm_capacity_share: float = 0.35,
    evidence_min: float = 0.4,
    max_slots: int = 20,
    member_weight: float = 1.0,
    risk_artifact: RiskArtifact | None = None,
    use_trained_risk: bool = True,
) -> dict[str, Any]:
    det = run_detectors(tables)
    graph, alerts = det.graph, det.alerts
    cases = build_cases(alerts, tables, det.strong)
    artifact = risk_artifact or (load_artifact() if use_trained_risk else None)
    risk_model = score_cases(cases, tables, det, artifact=artifact)
    for case in cases:
        case["expected_value"] = expected_value(case, horizon_days=horizon_days, recovery=recovery)
        case["ev"] = case["expected_value"]
    attach_rank_factors(cases, horizon_days=horizon_days, member_weight=member_weight)
    capacity = assign_lanes(
        cases,
        capacity_hours=capacity_hours,
        harm_capacity_share=harm_capacity_share,
        evidence_min=evidence_min,
        max_slots=max_slots,
    )
    selected = sum(1 for c in cases if c["lane"] in {"harm_priority", "selected"})
    return {
        "alerts": alerts,
        "cases": cases,
        "graph_nodes": graph.number_of_nodes(),
        "graph_edges": graph.number_of_edges(),
        "selected": selected,
        "capacity": capacity,
        "ranking_policy": ranking_policy(
            max_slots=max_slots, member_weight=member_weight, capacity_hours=capacity_hours
        ),
        "risk_model": risk_model,
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
                override_kinds=case.get("override_kinds") or [],
                severity=case["severity"],
                members_affected=case["members_affected"],
                flagged_dollars=case["flagged_dollars"],
                evidence_strength=case["evidence_strength"],
                estimated_hours=case["estimated_hours"],
                p_confirm=case["p_confirm"],
                expected_value=float(case.get("expected_value") or case.get("ev") or 0.0),
                f30=case["f30"],
                f60=case["f60"],
                f90=case["f90"],
            )
        )
        risk = case.get("risk") or {}
        session.add(
            CaseRisk(
                case_id=case["case_id"],
                run_id=run_id,
                score_kind=str(risk.get("score_kind") or "uncalibrated_heuristic"),
                model_version=str(risk.get("model_version") or "unknown"),
                calibrated=bool(risk.get("calibrated")),
                detail=risk,
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
    max_slots: int | None = None,
    member_weight: float | None = None,
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
    slots = int(max_slots if max_slots is not None else settings.max_queue_slots)
    impact = float(member_weight if member_weight is not None else settings.default_member_weight)
    result = detect(
        tables,
        horizon_days=horizon_days,
        recovery=settings.default_recovery_rate,
        capacity_hours=capacity_hours,
        harm_capacity_share=settings.harm_capacity_share,
        evidence_min=settings.evidence_strength_min,
        max_slots=slots,
        member_weight=impact,
        risk_artifact=load_artifact(default_path(settings)),
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
        "capacity": result["capacity"],
        "max_slots": slots,
        "member_weight": impact,
        "ranking_policy": result["ranking_policy"],
        "risk_model": result["risk_model"],
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
    max_slots: int | None = None,
    member_weight: float | None = None,
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
            max_slots=max_slots,
            member_weight=member_weight,
            now=instant,
        )
    return batch, run


def load_csv_batch(
    session: Session,
    *,
    user: User,
    settings: Settings,
    dataset: Dataset,
    source: dict[str, Any],
    horizon_days: int = 60,
    capacity_hours: float = 40.0,
    max_slots: int | None = None,
    member_weight: float | None = None,
    run_now: bool = True,
) -> tuple[Batch, PipelineRun | None]:
    instant = datetime.now(UTC)
    report = persist_dataset(session, dataset)
    batch = Batch(
        batch_id=report["batch_tag"],
        adapter="s3_csv",
        status="loaded",
        profile=dataset.profile,
        seed=dataset.seed,
        load_report={
            "tables": report["tables"],
            "ground_truth_rows": report["ground_truth_rows"],
            "scheme_ids": report["scheme_ids"],
            "data_card": report["data_card"],
            "source": source,
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
        payload={"adapter": "s3_csv", "bucket": source.get("bucket"), "key": source.get("key")},
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
            max_slots=max_slots,
            member_weight=member_weight,
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
    max_slots: int | None = None,
    member_weight: float | None = None,
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
        max_slots=max_slots,
        member_weight=member_weight,
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
