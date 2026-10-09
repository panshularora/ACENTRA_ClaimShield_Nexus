from __future__ import annotations

from fastapi import APIRouter, Depends, Request, Response
from pydantic import BaseModel, EmailStr, Field
from sqlalchemy.orm import Session

from claimshield.api.cookies import clear_auth_cookies, set_auth_cookies
from claimshield.api.deps import check_csrf, get_current_user, get_db
from claimshield.auth.rbac import PERMISSIONS, Role
from claimshield.auth.service import authenticate, logout, rotate_refresh, user_from_access
from claimshield.core.config import Settings, get_settings
from claimshield.core.errors import Forbidden, Unauthorized
from claimshield.db.models import User

router = APIRouter(prefix="/api/v1/auth", tags=["auth"])


class LoginBody(BaseModel):
    email: EmailStr
    password: str = Field(min_length=4, max_length=256)


class UserOut(BaseModel):
    id: str
    email: str
    role: str
    display_name: str
    permissions: list[str]
    csrf_token: str | None = None


def _permissions(role: str) -> list[str]:
    granted = PERMISSIONS[Role(role)]
    return sorted(granted)


@router.post("/login")
def login(
    body: LoginBody,
    request: Request,
    response: Response,
    session: Session = Depends(get_db),
    settings: Settings = Depends(get_settings),
) -> UserOut:
    ip = request.client.host if request.client else "unknown"
    user, _sess, access, refresh = authenticate(
        session,
        settings,
        email=body.email.lower(),
        password=body.password,
        ip=ip,
    )
    csrf = set_auth_cookies(response, settings, access=access, refresh=refresh, request=request)
    return UserOut(
        id=user.id,
        email=user.email,
        role=user.role,
        display_name=user.display_name,
        permissions=_permissions(user.role),
        csrf_token=csrf,
    )


@router.post("/refresh")
def refresh_session(
    request: Request,
    response: Response,
    session: Session = Depends(get_db),
    settings: Settings = Depends(get_settings),
) -> UserOut:
    token = request.cookies.get(settings.refresh_cookie_name)
    if not token:
        raise Unauthorized("missing refresh token")
    user, _sess, access, refresh = rotate_refresh(session, settings, refresh_token=token)
    csrf = set_auth_cookies(response, settings, access=access, refresh=refresh, request=request)
    return UserOut(
        id=user.id,
        email=user.email,
        role=user.role,
        display_name=user.display_name,
        permissions=_permissions(user.role),
        csrf_token=csrf,
    )


@router.post("/logout")
def logout_session(
    request: Request,
    response: Response,
    session: Session = Depends(get_db),
    settings: Settings = Depends(get_settings),
    _: None = Depends(check_csrf),
) -> dict[str, str]:
    token = request.cookies.get(settings.refresh_cookie_name)
    if token:
        logout(session, refresh_token=token)
    clear_auth_cookies(response, settings, request=request)
    return {"status": "logged_out"}


@router.get("/me")
def me(user: User = Depends(get_current_user)) -> UserOut:
    return UserOut(
        id=user.id,
        email=user.email,
        role=user.role,
        display_name=user.display_name,
        permissions=_permissions(user.role),
    )


class SessionOut(BaseModel):
    authenticated: bool
    user: UserOut | None = None
    refresh_available: bool = Field(
        default=False,
        description="No valid access token, but a refresh cookie is present: POST /auth/refresh may restore it.",
    )


@router.get("/session")
def session_status(
    request: Request,
    session: Session = Depends(get_db),
    settings: Settings = Depends(get_settings),
) -> SessionOut:
    """Who is signed in, answering 200 for anonymous visitors (unlike /me, which answers 401).

    Lets the landing and login pages check the session without a console error. It discloses
    nothing an anonymous caller does not already know: no token means ``authenticated: false``.
    """
    token = request.cookies.get(settings.access_cookie_name)
    if not token:
        header = request.headers.get("authorization") or ""
        token = header[7:] if header.lower().startswith("bearer ") else None
    refresh_available = bool(request.cookies.get(settings.refresh_cookie_name))
    if not token:
        return SessionOut(authenticated=False, refresh_available=refresh_available)
    try:
        user = user_from_access(session, settings, token)
    except (Unauthorized, Forbidden):
        return SessionOut(authenticated=False, refresh_available=refresh_available)
    return SessionOut(
        authenticated=True,
        user=UserOut(
            id=user.id,
            email=user.email,
            role=user.role,
            display_name=user.display_name,
            permissions=_permissions(user.role),
            csrf_token=request.cookies.get(settings.csrf_cookie_name),
        ),
    )
