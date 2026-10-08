from sqlalchemy.orm import Session

from claimshield.audit.service import append_event, verify_stored_chain
from claimshield.auth.service import seed_demo_users
from claimshield.core.config import Settings
from claimshield.db.base import Base
from claimshield.db.models import Alert, Case, User
from claimshield.db.session import create_engine, session_factory
from claimshield.pipeline.service import load_synthetic_batch
from claimshield.queue.knapsack import knapsack_select


def test_knapsack_respects_capacity() -> None:
    cases = [
        {"estimated_hours": 10, "ev": 50.0},
        {"estimated_hours": 20, "ev": 80.0},
        {"estimated_hours": 30, "ev": 90.0},
        {"estimated_hours": 5, "ev": 40.0},
    ]
    chosen = knapsack_select(cases, capacity_hours=25)
    hours = sum(c["estimated_hours"] for c in chosen)
    assert hours <= 25
    assert chosen


def test_load_tiny_batch_creates_cases_and_audit(tmp_path) -> None:
    url = f"sqlite+pysqlite:///{(tmp_path / 'p.db').as_posix()}"
    settings = Settings(database_url=url, jwt_signing_key="k")
    engine = create_engine(settings)
    Base.metadata.create_all(bind=engine)
    factory = session_factory(engine)
    with factory() as session:
        seed_demo_users(session)
        session.commit()
        user = session.query(User).filter_by(email="manager@demo.claimshield").one()
        batch, run = load_synthetic_batch(
            session,
            user=user,
            settings=settings,
            profile="tiny",
            seed=7,
            horizon_days=60,
            capacity_hours=40,
            run_now=True,
        )
        session.commit()
        assert batch.profile == "tiny"
        assert run is not None
        assert run.status == "completed"
        assert run.summary["n_alerts"] >= 10
        assert run.summary["n_cases"] >= 1
        n_cases = session.query(Case).filter_by(run_id=run.run_id).count()
        n_alerts = session.query(Alert).filter_by(run_id=run.run_id).count()
        assert n_cases == run.summary["n_cases"]
        assert n_alerts == run.summary["n_alerts"]
        assert verify_stored_chain(session) is True


def test_reload_same_seed_skips_existing_members(tmp_path) -> None:
    url = f"sqlite+pysqlite:///{(tmp_path / 'reload.db').as_posix()}"
    settings = Settings(database_url=url, jwt_signing_key="k")
    engine = create_engine(settings)
    Base.metadata.create_all(bind=engine)
    factory = session_factory(engine)
    with factory() as session:
        seed_demo_users(session)
        session.commit()
        user = session.query(User).filter_by(email="manager@demo.claimshield").one()
        first, first_run = load_synthetic_batch(
            session,
            user=user,
            settings=settings,
            profile="tiny",
            seed=7,
            horizon_days=60,
            capacity_hours=40,
            run_now=True,
        )
        session.commit()
        from claimshield.db.models import Member

        n_members = session.query(Member).count()
        second, second_run = load_synthetic_batch(
            session,
            user=user,
            settings=settings,
            profile="tiny",
            seed=7,
            horizon_days=90,
            capacity_hours=20,
            run_now=True,
        )
        session.commit()
        assert second.batch_id != first.batch_id
        assert second_run is not None and first_run is not None
        assert second_run.run_id != first_run.run_id
        assert second_run.status == "completed"
        assert second_run.summary["capacity_hours"] == 20
        skipped_members = next(
            row for row in second.load_report["tables"] if row["name"] == "member"
        )
        assert skipped_members["loaded"] == 0
        assert skipped_members["skipped"] == n_members
        assert session.query(Member).count() == n_members


def test_recompute_run_relanes_without_new_members(tmp_path) -> None:
    url = f"sqlite+pysqlite:///{(tmp_path / 'recompute.db').as_posix()}"
    settings = Settings(database_url=url, jwt_signing_key="k")
    engine = create_engine(settings)
    Base.metadata.create_all(bind=engine)
    factory = session_factory(engine)
    with factory() as session:
        seed_demo_users(session)
        session.commit()
        user = session.query(User).filter_by(email="manager@demo.claimshield").one()
        batch, first_run = load_synthetic_batch(
            session,
            user=user,
            settings=settings,
            profile="tiny",
            seed=7,
            horizon_days=60,
            capacity_hours=40,
            run_now=True,
        )
        session.commit()
        from claimshield.db.models import Member
        from claimshield.pipeline.service import recompute_run

        n_members = session.query(Member).count()
        second = recompute_run(
            session,
            user=user,
            settings=settings,
            batch=batch,
            horizon_days=90,
            capacity_hours=20,
        )
        session.commit()
        assert first_run is not None
        assert second.run_id != first_run.run_id
        assert second.batch_id == batch.batch_id
        assert second.summary["capacity_hours"] == 20
        assert second.summary["horizon_days"] == 90
        assert second.summary["recompute"] is True
        assert session.query(Member).count() == n_members
        case = session.query(Case).filter_by(run_id=second.run_id).first()
        assert case is not None
        assert case.sla_due is not None


def test_persisted_audit_chain_detects_tamper(tmp_path) -> None:
    url = f"sqlite+pysqlite:///{(tmp_path / 'a.db').as_posix()}"
    settings = Settings(database_url=url)
    engine = create_engine(settings)
    Base.metadata.create_all(bind=engine)
    factory = session_factory(engine)
    with Session(engine) as session:
        append_event(
            session,
            actor_id="USR-1",
            role="manager",
            action="batch.load",
            object_type="batch",
            object_id="BAT-1",
            payload={"rows": 3},
        )
        append_event(
            session,
            actor_id="USR-1",
            role="manager",
            action="run.start",
            object_type="run",
            object_id="RUN-1",
            payload={"ok": True},
        )
        session.commit()
        assert verify_stored_chain(session) is True
        from claimshield.db.models import AuditEvent

        event = session.query(AuditEvent).order_by(AuditEvent.seq.asc()).first()
        event.payload = {"rows": 999}
        session.commit()
        try:
            verify_stored_chain(session)
            raised = False
        except Exception:
            raised = True
        assert raised
