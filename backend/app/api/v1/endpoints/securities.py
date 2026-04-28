from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_user
from app.core.database import get_db
from app.models.user import User
from app.schemas.security import (
    SecurityCreate,
    SecurityEnsureRequest,
    SecurityEnsureResponse,
    SecurityResponse,
    SecuritySearchResult,
)
from app.services.security_service import (
    create_security,
    ensure_security_by_symbol,
    get_securities,
    get_security_by_symbol,
    search_securities,
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


@router.get("/search", response_model=list[SecuritySearchResult])
async def search_securities_endpoint(
    q: str = Query(..., min_length=1, max_length=50, description="심볼/회사명 부분일치"),
    limit: int = Query(20, ge=1, le=50),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """yfinance autocomplete 기반 종목 검색. DB 매칭된 row는 id가 채워진다."""
    hits = await search_securities(db, q, max_results=limit)
    return [
        SecuritySearchResult(
            symbol=h.symbol,
            name=h.name,
            currency=h.currency,
            exchange=h.exchange,
            asset_class=h.asset_class,  # type: ignore[arg-type]
            id=h.id,
        )
        for h in hits
    ]


@router.post("/ensure", response_model=SecurityEnsureResponse)
async def ensure_security_endpoint(
    body: SecurityEnsureRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """심볼로 Security를 보장(없으면 생성)하고 현재가까지 함께 반환."""
    result = await ensure_security_by_symbol(db, body.symbol)
    sec = result.security
    return SecurityEnsureResponse(
        id=sec.id,
        symbol=sec.symbol,
        name=sec.name,
        currency=sec.currency,
        asset_class=sec.asset_class,
        exchange=sec.exchange,
        current_price=result.current_price,
    )


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
