from __future__ import annotations

import hashlib
import hmac
from collections.abc import Callable, Generator

from fastapi import Depends, Header, Request
from sqlalchemy import Engine
from sqlalchemy.orm import Session, sessionmaker

from claimshield.auth.rbac import require_permission
from claimshield.auth.service import user_from_access
from claimshield.core.config import Settings, get_settings
from claimshield.core.errors import ClaimShieldError, Unauthorized
from claimshield.db.models import User
from claimshield.db.session import create_engine, session_factory

_engine: Engine | None = None
_factory: sessionmaker[Session] | None = None


def get_engine() -> Engine | None:
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
    except ClaimShieldError as exc:
        if exc.persist_changes:
            db.commit()
        else:
            db.rollback()
        raise
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


def require(permission: str) -> Callable[..., User]:
    def dep(user: User = Depends(get_current_user)) -> User:
        require_permission(user.role, permission)
        return user

    return dep


def check_csrf(request: Request, settings: Settings = Depends(get_settings)) -> None:
    """Double-submit CSRF check for cookie-authenticated writes.

    A request that carries the auth cookies must echo the CSRF cookie in ``X-CSRF-Token``;
    a missing header is rejected. Bearer-token clients send no ambient credentials, so
    there is nothing for a cross-site request to ride on and the check does not apply.
    """
    cookies = request.cookies
    if not cookies.get(settings.access_cookie_name) and not cookies.get(settings.refresh_cookie_name):
        return
    header = request.headers.get("X-CSRF-Token") or ""
    cookie = cookies.get(settings.csrf_cookie_name) or ""
    if not header or not cookie or not hmac.compare_digest(header.encode(), cookie.encode()):
        raise Unauthorized("csrf check failed")


def _token_digest(value: str) -> bytes:
    return hashlib.sha256(value.encode("utf-8")).digest()


def require_internal_token(
    settings: Settings = Depends(get_settings),
    provided: str | None = Header(default=None, alias="X-ClaimShield-Internal-Token"),
) -> None:
    expected = settings.internal_token
    if not expected or not provided:
        raise Unauthorized("internal token required")
    if not hmac.compare_digest(_token_digest(expected), _token_digest(provided)):
        raise Unauthorized("internal token required")
