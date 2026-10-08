from __future__ import annotations

from datetime import UTC, datetime, timedelta

from sqlalchemy import select
from sqlalchemy.orm import Session

from claimshield.audit.service import append_event
from claimshield.auth.passwords import hash_password, verify_password
from claimshield.auth.rate_limit import SlidingWindowLimiter
from claimshield.auth.rbac import Role
from claimshield.auth.tokens import (
    decode_access_token,
    hash_refresh_token,
    issue_access_token,
    new_refresh_token,
)
from claimshield.core.clock import as_utc
from claimshield.core.config import Settings
from claimshield.core.errors import Forbidden, Unauthorized
from claimshield.core.ids import new_id
from claimshield.db.models import AuthSession, User

login_limiter = SlidingWindowLimiter(limit=5, window_seconds=60)

DEMO_USERS: list[dict[str, str]] = [
    {
        "email": "investigator@demo.claimshield",
        "role": Role.INVESTIGATOR.value,
        "display_name": "SIU Investigator",
        "password": "demo-investigator",
    },
    {
        "email": "investigator2@demo.claimshield",
        "role": Role.INVESTIGATOR.value,
        "display_name": "Unassigned Investigator",
        "password": "demo-investigator2",
    },
    {
        "email": "manager@demo.claimshield",
        "role": Role.MANAGER.value,
        "display_name": "SIU Manager",
        "password": "demo-manager",
    },
    {
        "email": "analyst@demo.claimshield",
        "role": Role.ANALYST.value,
        "display_name": "Policy Analyst",
        "password": "demo-analyst",
    },
    {
        "email": "auditor@demo.claimshield",
        "role": Role.AUDITOR.value,
        "display_name": "Compliance Auditor",
        "password": "demo-auditor",
    },
    {
        "email": "admin@demo.claimshield",
        "role": Role.ADMIN.value,
        "display_name": "Admin",
        "password": "demo-admin",
    },
]


def seed_demo_users(session: Session, now: datetime | None = None) -> None:
    instant = now or datetime.now(UTC)
    for spec in DEMO_USERS:
        existing = session.execute(select(User).where(User.email == spec["email"])).scalar_one_or_none()
        if existing:
            continue
        session.add(
            User(
                id=new_id("USR"),
                email=spec["email"],
                password_hash=hash_password(spec["password"]),
                role=spec["role"],
                display_name=spec["display_name"],
                is_active=True,
                created_at=instant,
            )
        )
    session.flush()


def authenticate(
    session: Session,
    settings: Settings,
    *,
    email: str,
    password: str,
    ip: str,
    now: datetime | None = None,
) -> tuple[User, AuthSession, str, str]:
    instant = now or datetime.now(UTC)
    login_limiter.check(f"{ip}:{email.lower()}", now=instant)
    user = session.execute(select(User).where(User.email == email.lower())).scalar_one_or_none()
    if user is None or not user.is_active or not verify_password(password, user.password_hash):
        raise Unauthorized("invalid email or password")
    refresh = new_refresh_token()
    auth_session = AuthSession(
        id=new_id("SID"),
        user_id=user.id,
        refresh_token_hash=hash_refresh_token(refresh),
        previous_refresh_hash=None,
        expires_at=instant + timedelta(hours=settings.refresh_hours),
        revoked_at=None,
        created_at=instant,
        last_used_at=instant,
    )
    session.add(auth_session)
    session.flush()
    access = issue_access_token(
        user_id=user.id,
        role=user.role,
        session_id=auth_session.id,
        settings=settings,
        now=instant,
    )
    append_event(
        session,
        actor_id=user.id,
        role=user.role,
        action="auth.login",
        object_type="session",
        object_id=auth_session.id,
        payload={"email": user.email},
        ts=instant,
    )
    return user, auth_session, access, refresh


def rotate_refresh(
    session: Session,
    settings: Settings,
    *,
    refresh_token: str,
    now: datetime | None = None,
) -> tuple[User, AuthSession, str, str]:
    instant = now or datetime.now(UTC)
    digest = hash_refresh_token(refresh_token)
    reuse = session.execute(
        select(AuthSession).where(AuthSession.previous_refresh_hash == digest)
    ).scalar_one_or_none()
    if reuse is not None:
        reuse.revoked_at = instant
        session.flush()
        raise Unauthorized("refresh token reuse detected; session revoked")
    auth_session = session.execute(
        select(AuthSession).where(AuthSession.refresh_token_hash == digest)
    ).scalar_one_or_none()
    if (
        auth_session is None
        or auth_session.revoked_at is not None
        or as_utc(auth_session.expires_at) <= instant
    ):
        raise Unauthorized("invalid refresh token")
    user = session.get(User, auth_session.user_id)
    if user is None or not user.is_active:
        raise Unauthorized("user disabled")
    new_refresh = new_refresh_token()
    auth_session.previous_refresh_hash = auth_session.refresh_token_hash
    auth_session.refresh_token_hash = hash_refresh_token(new_refresh)
    auth_session.last_used_at = instant
    session.flush()
    access = issue_access_token(
        user_id=user.id,
        role=user.role,
        session_id=auth_session.id,
        settings=settings,
        now=instant,
    )
    return user, auth_session, access, new_refresh


def logout(session: Session, *, refresh_token: str, now: datetime | None = None) -> None:
    instant = now or datetime.now(UTC)
    digest = hash_refresh_token(refresh_token)
    auth_session = session.execute(
        select(AuthSession).where(AuthSession.refresh_token_hash == digest)
    ).scalar_one_or_none()
    if auth_session is None:
        return
    auth_session.revoked_at = instant
    user = session.get(User, auth_session.user_id)
    append_event(
        session,
        actor_id=auth_session.user_id,
        role=user.role if user else "unknown",
        action="auth.logout",
        object_type="session",
        object_id=auth_session.id,
        payload={},
        ts=instant,
    )


def user_from_access(session: Session, settings: Settings, token: str) -> User:
    claims = decode_access_token(token, settings)
    user = session.get(User, claims["sub"])
    if user is None or not user.is_active:
        raise Unauthorized("user not found")
    auth_session = session.get(AuthSession, claims["sid"])
    if auth_session is None or auth_session.revoked_at is not None:
        raise Unauthorized("session revoked")
    if user.role != claims["role"]:
        raise Forbidden("role claim mismatch")
    return user
