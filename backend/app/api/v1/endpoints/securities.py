from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_user
from app.core.database import get_db
from app.models.user import User
from app.schemas.security import SecurityCreate, SecurityResponse
from app.services.security_service import (
    create_security,
    get_securities,
    get_security_by_symbol,
)

router = APIRouter(tags=["securities"])


@router.get("", response_model=list[SecurityResponse])
async def list_securities(
    symbol: str | None = Query(None, description="심볼로 필터 (정확 일치)"),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    if symbol:
        sec = await get_security_by_symbol(db, symbol)
        return [sec] if sec else []
    return await get_securities(db)


@router.post("", response_model=SecurityResponse, status_code=201)
async def create_security_endpoint(
    body: SecurityCreate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    existing = await get_security_by_symbol(db, body.symbol)
    if existing:
        raise HTTPException(
            status_code=409,
            detail=f"Security already exists: id={existing.id}",
        )
    return await create_security(db, body.model_dump())
