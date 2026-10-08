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
