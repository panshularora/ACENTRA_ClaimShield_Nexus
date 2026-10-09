from __future__ import annotations

from pathlib import Path

from fastapi import FastAPI, HTTPException
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles

from claimshield.core.config import Settings

_API_PREFIXES = ("api/", "healthz", "readyz", "docs", "redoc", "openapi")


def discover_spa_dir(settings: Settings) -> Path | None:
    if settings.spa_dir is not None:
        configured = settings.spa_dir
        return configured if (configured / "index.html").is_file() else None
    here = Path(__file__).resolve()
    candidates = (here.parents[3] / "spa",)
    for path in candidates:
        if (path / "index.html").is_file():
            return path
    return None


def attach_spa(app: FastAPI, settings: Settings) -> None:
    """Serve the Vite build so /login and desk paths work on the FastAPI host."""
    root = discover_spa_dir(settings)
    if root is None:
        return
    root = root.resolve()
    for name in ("assets", "brand"):
        folder = root / name
        if folder.is_dir():
            app.mount(f"/{name}", StaticFiles(directory=folder), name=f"spa-{name}")

    @app.get("/{full_path:path}", include_in_schema=False)
    async def spa_fallback(full_path: str) -> FileResponse:
        if full_path.startswith(_API_PREFIXES):
            raise HTTPException(status_code=404)
        target = (root / full_path).resolve()
        try:
            target.relative_to(root)
        except ValueError as exc:
            raise HTTPException(status_code=404) from exc
        if target.is_file():
            return FileResponse(target)
        return FileResponse(root / "index.html")
