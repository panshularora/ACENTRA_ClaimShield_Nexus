"""Vercel Python entrypoint. Re-exports the FastAPI app."""

from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent / "src"))

from claimshield.api.main import app

__all__ = ["app"]
