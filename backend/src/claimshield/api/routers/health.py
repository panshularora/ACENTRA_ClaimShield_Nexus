from typing import Any

from fastapi import APIRouter, Depends

from claimshield.auth.service import DEMO_USERS
from claimshield.core.config import Settings, get_settings

router = APIRouter(tags=["health"])


@router.get("/healthz")
def healthz() -> dict[str, str]:
    return {"status": "ok"}


@router.get("/readyz")
def readyz() -> dict[str, str]:
    return {"status": "ready"}


@router.get("/api/v1/meta")
def meta(settings: Settings = Depends(get_settings)) -> dict[str, Any]:
    body: dict[str, Any] = {
        "name": "ClaimShield Nexus",
        "version": "0.1.0",
        "demo_mode": settings.demo_mode,
        "data_profile": settings.data_profile,
    }
    if settings.demo_mode:
        body["demo_users"] = [
            {"email": u["email"], "role": u["role"], "password": u["password"]}
            for u in DEMO_USERS
        ]
    return body
