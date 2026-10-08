"""Prefixed identifiers used across ClaimShield tables."""

from __future__ import annotations

import secrets
import string
from typing import Final

ALPHABET: Final = string.ascii_uppercase + string.digits


def new_id(prefix: str, length: int = 10) -> str:
    body = "".join(secrets.choice(ALPHABET) for _ in range(length))
    return f"{prefix}-{body}"
