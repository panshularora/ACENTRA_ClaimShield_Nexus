from __future__ import annotations

from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from claimshield.api.deps import get_db, require
from claimshield.cases.common import get_case_or_404
from claimshield.cases.network import entity_summary
from claimshield.cases.network_models import EntitySummary
from claimshield.db.models import User

router = APIRouter(prefix="/api/v1/entities", tags=["entities"])


@router.get("/{entity_id}/summary", response_model=EntitySummary, response_model_exclude_none=True)
def get_entity_summary(
    entity_id: str,
    case_id: str = Query(max_length=32, description="Scope: the entity must be in this case's network."),
    unmask: bool = Query(default=False),
    session: Session = Depends(get_db),
    user: User = Depends(require("case:read")),
) -> EntitySummary:
    """All claims on file, run-wide findings and related cases for a node of a case network."""
    case = get_case_or_404(session, case_id)
    return entity_summary(session, case, user, entity_id, unmask=unmask)
