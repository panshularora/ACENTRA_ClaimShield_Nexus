from __future__ import annotations

from collections.abc import Mapping
from enum import StrEnum
from typing import Final

from claimshield.core.errors import Forbidden


class Role(StrEnum):
    INVESTIGATOR = "investigator"
    MANAGER = "manager"
    ANALYST = "analyst"
    AUDITOR = "auditor"
    ADMIN = "admin"


PERMISSIONS: Final[Mapping[Role, frozenset[str]]] = {
    Role.INVESTIGATOR: frozenset(
        {
            "queue:read",
            "case:read",
            "case:decide",
            "case:assign",
            "member:unmask",
            "wiki:read",
            "rule:read",
        }
    ),
    Role.MANAGER: frozenset(
        {
            "batch:load",
            "batch:read",
            "run:start",
            "run:read",
            "queue:read",
            "queue:configure",
            "case:read",
            "case:decide",
            "case:assign",
            "decision:approve",
            "rule:read",
            "rule:activate",
            "wiki:read",
            "wiki:approve",
            "model:read",
            "outcomes:read",
        }
    ),
    Role.ANALYST: frozenset(
        {
            "batch:read",
            "run:read",
            "rule:read",
            "rule:write",
            "rule:simulate",
            "rule:activate",
            "wiki:read",
            "wiki:approve",
            "model:read",
            "outcomes:read",
        }
    ),
    Role.AUDITOR: frozenset(
        {
            "audit:read",
            "audit:export",
            "model:read",
            "outcomes:read",
            "wiki:read",
            "rule:read",
            "case:read",
        }
    ),
    Role.ADMIN: frozenset(
        {
            "admin:*",
            "audit:read",
            "audit:export",
        }
    ),
}


def has_permission(role: Role | str, permission: str) -> bool:
    resolved = Role(role)
    granted = PERMISSIONS[resolved]
    return permission in granted or "admin:*" in granted


def require_permission(role: Role | str, permission: str) -> None:
    if not has_permission(role, permission):
        raise Forbidden(f"role {role} lacks {permission}")
