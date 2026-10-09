from sqlalchemy import create_engine, inspect, text

from claimshield.db.base import Base
from claimshield.db.models import Case, Decision
from claimshield.db.session import ensure_sqlite_columns


def test_ensure_sqlite_columns_adds_override_kinds(tmp_path) -> None:
    engine = create_engine(f"sqlite+pysqlite:///{(tmp_path / 'old.db').as_posix()}")
    with engine.begin() as conn:
        conn.execute(
            text(
                'CREATE TABLE "case" ('
                "case_id VARCHAR(32) NOT NULL PRIMARY KEY, "
                "run_id VARCHAR(32) NOT NULL, "
                "status VARCHAR(24) NOT NULL, "
                "lane VARCHAR(32) NOT NULL, "
                "assignee_id VARCHAR(32), "
                "sla_due DATE, "
                "primary_entity_id VARCHAR(32) NOT NULL, "
                "primary_entity_type VARCHAR(16) NOT NULL, "
                "entity_ids JSON NOT NULL, "
                "harm INTEGER NOT NULL, "
                "severity INTEGER NOT NULL, "
                "members_affected INTEGER NOT NULL, "
                "flagged_dollars FLOAT NOT NULL, "
                "evidence_strength FLOAT NOT NULL, "
                "estimated_hours FLOAT NOT NULL, "
                "p_confirm FLOAT NOT NULL, "
                "expected_value FLOAT NOT NULL, "
                "f30 FLOAT, f60 FLOAT, f90 FLOAT)"
            )
        )
        conn.execute(
            text(
                "CREATE TABLE decision ("
                "decision_id VARCHAR(32) NOT NULL PRIMARY KEY, "
                "case_id VARCHAR(32) NOT NULL, "
                "actor_id VARCHAR(32) NOT NULL, "
                "action VARCHAR(32) NOT NULL, "
                "ladder_step VARCHAR(64), "
                "reason TEXT NOT NULL, "
                "evidence_refs JSON NOT NULL, "
                "approved_by VARCHAR(32), "
                "created_at DATETIME NOT NULL)"
            )
        )
    ensure_sqlite_columns(engine)
    cols = {c["name"] for c in inspect(engine).get_columns("case")}
    assert "override_kinds" in cols
    decision_cols = {c["name"] for c in inspect(engine).get_columns("decision")}
    assert {"status", "prior_status", "approved_at", "review_note"} <= decision_cols
    with engine.begin() as conn:
        conn.execute(
            text(
                'INSERT INTO "case" (case_id, run_id, status, lane, primary_entity_id, '
                "primary_entity_type, entity_ids, harm, override_kinds, severity, "
                "members_affected, flagged_dollars, evidence_strength, estimated_hours, "
                "p_confirm, expected_value) VALUES "
                "('CASE-1', 'RUN-1', 'open', 'selected', 'PRV-1', 'provider', '[]', "
                "1, '[\"after_death\"]', 1, 0, 0, 0, 8, 0, 0)"
            )
        )
    assert Case.__table__.c.override_kinds is not None
    assert Decision.__table__.c.status is not None
    # Metadata import keeps Base populated for the helper.
    assert "case" in Base.metadata.tables
