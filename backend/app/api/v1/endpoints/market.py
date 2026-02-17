from fastapi import APIRouter, Depends, HTTPException, Query

from app.api.deps import get_current_user
from app.core.redis import get_redis
from app.models.asset import AssetType
from app.models.user import User
from app.schemas.market import (
    PriceResponse, ExchangeRateResponse,
    MarketTrendsResponse, MarketSearchResponse,
)
from app.services.market_service import MarketService

router = APIRouter(prefix="/market", tags=["market"])


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

    # exchange → AssetType 매핑 (힌트)
    asset_type_map = {
        "KRX": AssetType.STOCK_KR,
        "NASDAQ": AssetType.STOCK_US,
        "NYSE": AssetType.STOCK_US,
        "NYSEARCA": AssetType.GOLD,
    }
    asset_type = asset_type_map.get(exchange) if exchange else None

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
