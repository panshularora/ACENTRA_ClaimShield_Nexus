from __future__ import annotations

from collections.abc import Iterator
from contextlib import contextmanager

from sqlalchemy import create_engine as sa_create_engine
from sqlalchemy import inspect, text
from sqlalchemy.engine import Engine
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.pool import StaticPool
from sqlalchemy.sql.schema import Column

from claimshield.core.config import Settings, get_settings
from claimshield.db.base import Base


def create_engine(settings: Settings | None = None) -> Engine:
    cfg = settings or get_settings()
    url = cfg.database_url
    kwargs: dict[str, object] = {"future": True}
    if url.startswith("sqlite"):
        kwargs["connect_args"] = {"check_same_thread": False}
        if ":memory:" in url:
            kwargs["poolclass"] = StaticPool
    return sa_create_engine(url, **kwargs)


def _sqlite_default_sql(col: Column[object]) -> str | None:
    """Literal DEFAULT for ALTER TABLE ADD COLUMN on an existing SQLite file."""
    arg = col.default.arg if col.default is not None else None
    if callable(arg):
        try:
            arg = arg()
        except TypeError:
            arg = None
    if arg == [] or (arg is None and col.type.__class__.__name__ == "JSON"):
        return "'[]'"
    if arg == {}:
        return "'{}'"
    if isinstance(arg, bool):
        return "1" if arg else "0"
    if isinstance(arg, int | float):
        return str(arg)
    if isinstance(arg, str):
        return "'" + arg.replace("'", "''") + "'"
    return None


def ensure_sqlite_columns(engine: Engine) -> None:
    """Add columns that ``create_all`` skipped on an already-created SQLite file.

    New tables appear automatically. New columns on existing tables (for example
    ``case.override_kinds`` after a git pull) do not, and INSERTs then 500.
    """
    if engine.dialect.name != "sqlite":
        return
    from claimshield.db import models as _models  # noqa: F401

    insp = inspect(engine)
    present = set(insp.get_table_names())
    preparer = engine.dialect.identifier_preparer
    with engine.begin() as conn:
        for table in Base.metadata.sorted_tables:
            if table.name not in present:
                continue
            existing = {c["name"] for c in insp.get_columns(table.name)}
            for col in table.columns:
                if col.name in existing:
                    continue
                type_sql = col.type.compile(dialect=engine.dialect)
                ddl = (
                    f"ALTER TABLE {preparer.quote(table.name)} "
                    f"ADD COLUMN {preparer.quote(col.name)} {type_sql}"
                )
                if col.nullable:
                    ddl += " NULL"
                else:
                    default_sql = _sqlite_default_sql(col)
                    if default_sql is None:
                        raise RuntimeError(
                            f"cannot add NOT NULL {table.name}.{col.name} without a default"
                        )
                    ddl += f" NOT NULL DEFAULT {default_sql}"
                conn.execute(text(ddl))
            insp.clear_cache()


def session_factory(engine: Engine) -> sessionmaker[Session]:
    return sessionmaker(bind=engine, autoflush=False, autocommit=False, future=True)


@contextmanager
def session_scope(factory: sessionmaker[Session]) -> Iterator[Session]:
    session = factory()
    try:
        yield session
        session.commit()
    except Exception:
        session.rollback()
        raise
    finally:
        session.close()
