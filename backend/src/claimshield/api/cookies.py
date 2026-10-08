from __future__ import annotations

import secrets

from fastapi import Request, Response

from claimshield.core.config import Settings


def cookie_policy(settings: Settings, request: Request | None = None) -> tuple[bool, str]:
    """SameSite=None; Secure when the browser origin is a public HTTPS site (Vercel)."""
    origin = request.headers.get("origin") if request is not None else ""
    origin = origin or ""
    if origin.startswith("https://") and "localhost" not in origin and "127.0.0.1" not in origin:
        return True, "none"
    return settings.cookie_secure, settings.cookie_samesite


def set_auth_cookies(
    response: Response,
    settings: Settings,
    *,
    access: str,
    refresh: str,
    request: Request | None = None,
) -> str:
    csrf = secrets.token_urlsafe(24)
    secure, samesite = cookie_policy(settings, request)
    for name, value in ((settings.access_cookie_name, access), (settings.refresh_cookie_name, refresh)):
        response.set_cookie(
            name,
            value,
            httponly=True,
            secure=secure,
            samesite=samesite,  # type: ignore[arg-type]
            path="/",
        )
    response.set_cookie(
        settings.csrf_cookie_name,
        csrf,
        httponly=False,
        secure=secure,
        samesite=samesite,  # type: ignore[arg-type]
        path="/",
    )
    return csrf


def clear_auth_cookies(response: Response, settings: Settings, request: Request | None = None) -> None:
    secure, samesite = cookie_policy(settings, request)
    for name in (
        settings.access_cookie_name,
        settings.refresh_cookie_name,
        settings.csrf_cookie_name,
    ):
        response.delete_cookie(name, path="/", secure=secure, samesite=samesite)  # type: ignore[arg-type]
