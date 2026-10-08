from __future__ import annotations

from collections.abc import Generator

from fastapi import Cookie, Depends, Header, Request
from sqlalchemy.orm import Session, sessionmaker

from claimshield.auth.rbac import require_permission
from claimshield.auth.service import user_from_access
from claimshield.core.config import Settings, get_settings
from claimshield.core.errors import Unauthorized
from claimshield.db.models import User
from claimshield.db.session import create_engine, session_factory

_engine = None
_factory: sessionmaker[Session] | None = None


def get_engine():
    return _engine


def configure_engine(settings: Settings | None = None) -> sessionmaker[Session]:
    global _engine, _factory
    _engine = create_engine(settings or get_settings())
    _factory = session_factory(_engine)
    return _factory


def reset_engine() -> None:
    global _engine, _factory
    if _engine is not None:
        _engine.dispose()
    _engine = None
    _factory = None


def get_db() -> Generator[Session, None, None]:
    if _factory is None:
        configure_engine()
    assert _factory is not None
    db = _factory()
    try:
        yield db
        db.commit()
    except Exception:
        db.rollback()
        raise
    finally:
        db.close()


def get_access_token(
    request: Request,
    settings: Settings = Depends(get_settings),
) -> str:
    token = request.cookies.get(settings.access_cookie_name)
    if not token:
        header = request.headers.get("authorization") or ""
        if header.lower().startswith("bearer "):
            token = header[7:]
    if not token:
        raise Unauthorized("not authenticated")
    return token


def get_current_user(
    session: Session = Depends(get_db),
    settings: Settings = Depends(get_settings),
    token: str = Depends(get_access_token),
) -> User:
    return user_from_access(session, settings, token)


def require(permission: str):
    def dep(user: User = Depends(get_current_user)) -> User:
        require_permission(user.role, permission)
        return user

    return dep


def check_csrf(
    settings: Settings = Depends(get_settings),
    csrf_header: str | None = Header(default=None, alias="X-CSRF-Token"),
    csrf_cookie: str | None = Cookie(default=None, alias="cs_csrf"),
) -> None:
    if not settings.cookie_secure and csrf_header is None:
        return
    if not csrf_header or not csrf_cookie or csrf_header != csrf_cookie:
        raise Unauthorized("csrf check failed")
