from __future__ import annotations

import hashlib
import secrets
from datetime import UTC, datetime, timedelta
from typing import Any

import jwt

from claimshield.core.config import Settings
from claimshield.core.errors import Unauthorized


def issue_access_token(
    *,
    user_id: str,
    role: str,
    session_id: str,
    settings: Settings,
    now: datetime | None = None,
) -> str:
    instant = now or datetime.now(UTC)
    payload: dict[str, Any] = {
        "sub": user_id,
        "role": role,
        "sid": session_id,
        "exp": instant + timedelta(minutes=settings.jwt_access_minutes),
        "iat": instant,
        "jti": secrets.token_urlsafe(12),
    }
    return jwt.encode(payload, settings.jwt_signing_key, algorithm="HS256")


def decode_access_token(token: str, settings: Settings) -> dict[str, Any]:
    try:
        return jwt.decode(token, settings.jwt_signing_key, algorithms=["HS256"])
    except jwt.PyJWTError as exc:
        raise Unauthorized("invalid or expired access token") from exc


def new_refresh_token() -> str:
    return secrets.token_urlsafe(48)


def hash_refresh_token(token: str) -> str:
    return hashlib.sha256(token.encode("utf-8")).hexdigest()
