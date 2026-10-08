from __future__ import annotations

from fastapi import APIRouter, Depends, Request, Response
from pydantic import BaseModel, EmailStr, Field
from sqlalchemy.orm import Session

from claimshield.api.cookies import clear_auth_cookies, set_auth_cookies
from claimshield.api.deps import check_csrf, get_current_user, get_db
from claimshield.auth.rbac import PERMISSIONS, Role
from claimshield.auth.service import authenticate, logout, rotate_refresh
from claimshield.core.config import Settings, get_settings
from claimshield.core.errors import Unauthorized
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
    csrf = set_auth_cookies(response, settings, access=access, refresh=refresh)
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
    csrf = set_auth_cookies(response, settings, access=access, refresh=refresh)
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
    clear_auth_cookies(response, settings)
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
