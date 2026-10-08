from __future__ import annotations

import secrets

from fastapi import Response

from claimshield.core.config import Settings


def set_auth_cookies(response: Response, settings: Settings, *, access: str, refresh: str) -> str:
    csrf = secrets.token_urlsafe(24)
    for name, value in ((settings.access_cookie_name, access), (settings.refresh_cookie_name, refresh)):
        response.set_cookie(
            name,
            value,
            httponly=True,
            secure=settings.cookie_secure,
            samesite=settings.cookie_samesite,
            path="/",
        )
    response.set_cookie(
        settings.csrf_cookie_name,
        csrf,
        httponly=False,
        secure=settings.cookie_secure,
        samesite=settings.cookie_samesite,
        path="/",
    )
    return csrf


def clear_auth_cookies(response: Response, settings: Settings) -> None:
    for name in (
        settings.access_cookie_name,
        settings.refresh_cookie_name,
        settings.csrf_cookie_name,
    ):
        response.delete_cookie(name, path="/")
