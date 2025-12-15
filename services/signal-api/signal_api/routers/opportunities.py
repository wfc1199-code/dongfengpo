"""Routes for opportunity data."""

from __future__ import annotations

from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException, Query

from ..dependencies import get_repository
from ..models import Opportunity
from ..repository import OpportunityRepository

router = APIRouter(prefix="/opportunities", tags=["opportunities"])


@router.get("", response_model=List[Opportunity])
async def list_opportunities(
    limit: int = Query(20, ge=1, le=200),
    state: Optional[str] = Query(None),
    repository: OpportunityRepository = Depends(get_repository),
) -> List[Opportunity]:
    return await repository.list_opportunities(limit=limit, state=state)


@router.get("/{symbol}", response_model=Opportunity)
async def get_opportunity(
    symbol: str,
    repository: OpportunityRepository = Depends(get_repository),
) -> Opportunity:
    opportunity = await repository.get_opportunity(symbol)
    if not opportunity:
        raise HTTPException(status_code=404, detail="Opportunity not found")
    return opportunity
