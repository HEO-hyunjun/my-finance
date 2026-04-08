from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_user
from app.core.database import get_db
from app.core.redis import get_redis
from app.models.entry import Entry
from app.models.security import AssetClass, Security
from app.models.user import User
from app.schemas.market import (
    PriceResponse, ExchangeRateResponse,
    MarketTrendsResponse, MarketSearchResponse,
)
from app.services.market_service import MarketService

ASSET_CLASS_MAP = {
    "stock_kr": AssetClass.EQUITY_KR,
    "stock_us": AssetClass.EQUITY_US,
    "gold": AssetClass.COMMODITY,
    "equity_kr": AssetClass.EQUITY_KR,
    "equity_us": AssetClass.EQUITY_US,
    "commodity": AssetClass.COMMODITY,
}


class RefreshPriceRequest(BaseModel):
    symbol: str
    asset_type: str | None = None

router = APIRouter(tags=["market"])


@router.get("/price", response_model=PriceResponse)
async def get_price(
    symbol: str = Query(..., description="종목코드/티커 (예: TSLA, 005930, GLD)"),
    exchange: str | None = Query(
        default=None,
        description="거래소 (KRX, NASDAQ, NYSE, NYSEARCA)",
    ),
    current_user: User = Depends(get_current_user),
    redis=Depends(get_redis),
):
    market = MarketService(redis)

    # exchange → AssetClass 매핑 (힌트)
    asset_class_map = {
        "KRX": AssetClass.EQUITY_KR,
        "NASDAQ": AssetClass.EQUITY_US,
        "NYSE": AssetClass.EQUITY_US,
        "NYSEARCA": AssetClass.COMMODITY,
    }
    asset_type = asset_class_map.get(exchange) if exchange else None

    try:
        return await market.get_price(symbol, asset_type)
    except Exception as e:
        raise HTTPException(status_code=503, detail=f"Market data unavailable: {e}")


@router.get("/exchange-rate", response_model=ExchangeRateResponse)
async def get_exchange_rate(
    current_user: User = Depends(get_current_user),
    redis=Depends(get_redis),
):
    market = MarketService(redis)
    try:
        return await market.get_exchange_rate()
    except Exception as e:
        raise HTTPException(status_code=503, detail=f"Exchange rate unavailable: {e}")


@router.get("/trends", response_model=MarketTrendsResponse)
async def get_market_trends(
    current_user: User = Depends(get_current_user),
    redis=Depends(get_redis),
):
    market = MarketService(redis)
    try:
        return await market.get_market_trends()
    except Exception as e:
        raise HTTPException(status_code=503, detail=f"Market trends unavailable: {e}")


@router.get("/search", response_model=MarketSearchResponse)
async def search_market(
    query: str = Query(..., description="검색어 (종목명 또는 티커)"),
    current_user: User = Depends(get_current_user),
    redis=Depends(get_redis),
):
    market = MarketService(redis)
    try:
        return await market.search_market(query)
    except Exception as e:
        raise HTTPException(status_code=503, detail=f"Market search unavailable: {e}")


@router.post("/refresh-price", response_model=PriceResponse)
async def refresh_price(
    body: RefreshPriceRequest,
    current_user: User = Depends(get_current_user),
    redis=Depends(get_redis),
):
    """특정 심볼의 시세를 강제로 새로고침하여 캐시에 저장."""
    market = MarketService(redis)
    asset_type = ASSET_CLASS_MAP.get(body.asset_type) if body.asset_type else None

    try:
        # 미국주식이면 환율도 함께 갱신
        if asset_type in (AssetClass.EQUITY_US,):
            await market.get_exchange_rate()

        return await market.get_price(body.symbol, asset_type)
    except Exception as e:
        raise HTTPException(status_code=503, detail=f"Price refresh failed: {e}")


@router.post("/refresh-exchange-rate", response_model=ExchangeRateResponse)
async def refresh_exchange_rate(
    current_user: User = Depends(get_current_user),
    redis=Depends(get_redis),
):
    """환율을 강제로 새로고침하여 캐시에 저장."""
    market = MarketService(redis)
    try:
        return await market.get_exchange_rate()
    except Exception as e:
        raise HTTPException(status_code=503, detail=f"Exchange rate refresh failed: {e}")


@router.post("/refresh-all")
async def refresh_all_prices(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
    redis=Depends(get_redis),
):
    """현재 유저의 모든 보유 증권 시세 + 환율을 일괄 새로고침."""
    market = MarketService(redis)

    stmt = (
        select(Security)
        .join(Entry, Entry.security_id == Security.id)
        .where(Entry.user_id == current_user.id)
        .group_by(Security.id)
    )
    result = await db.execute(stmt)
    securities = result.scalars().all()
    symbol_pairs = [(s.symbol, s.asset_class) for s in securities]

    results = await market.warm_cache_for_symbols(symbol_pairs)

    success = sum(1 for v in results.values() if v)
    failed = sum(1 for v in results.values() if not v)
    return {"success": success, "failed": failed, "total": len(results)}
