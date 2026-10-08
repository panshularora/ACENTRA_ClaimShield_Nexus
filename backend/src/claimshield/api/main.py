from __future__ import annotations

from contextlib import asynccontextmanager

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from claimshield.api.deps import configure_engine, get_engine
from claimshield.api.routers import audit as audit_router
from claimshield.api.routers import auth as auth_router
from claimshield.api.routers import aws as aws_router
from claimshield.api.routers import batches as batches_router
from claimshield.api.routers import cases as cases_router
from claimshield.api.routers import decisions as decisions_router
from claimshield.api.routers import health as health_router
from claimshield.api.routers import models as models_router
from claimshield.api.routers import wiki as wiki_router
from claimshield.auth.service import seed_demo_users, seed_system_user
from claimshield.core.config import get_settings
from claimshield.core.errors import ClaimShieldError
from claimshield.db import models as _models  # noqa: F401
from claimshield.db.base import Base


@asynccontextmanager
async def lifespan(_app: FastAPI):
    settings = get_settings()
    factory = configure_engine(settings)
    engine = get_engine()
    assert engine is not None
    Base.metadata.create_all(bind=engine)
    with factory() as session:
        seed_demo_users(session)
        seed_system_user(session)
        session.commit()
    yield


def create_app() -> FastAPI:
    app = FastAPI(
        title="ClaimShield Nexus",
        version="0.1.0",
        openapi_url="/api/v1/openapi.json",
        lifespan=lifespan,
    )

    @app.exception_handler(ClaimShieldError)
    async def domain_error(_: Request, exc: ClaimShieldError) -> JSONResponse:
        return JSONResponse(status_code=exc.status, content=exc.to_problem())

    app.add_middleware(
        CORSMiddleware,
        allow_origins=["http://localhost:5173", "http://127.0.0.1:5173"],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )
    app.include_router(health_router.router)
    app.include_router(auth_router.router)
    app.include_router(batches_router.router)
    app.include_router(cases_router.router)
    app.include_router(audit_router.router)
    app.include_router(wiki_router.router)
    app.include_router(decisions_router.router)
    app.include_router(aws_router.router)
    app.include_router(models_router.router)
    return app


app = create_app()
