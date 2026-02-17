from pydantic import BaseModel


class PriceResponse(BaseModel):
    symbol: str
    name: str | None = None
    price: float
    currency: str
    change: float | None = None
    change_percent: float | None = None
    is_market_open: bool = True
    cached: bool = False


class ExchangeRateResponse(BaseModel):
    pair: str = "USD/KRW"
    rate: float
    change: float | None = None
    change_percent: float | None = None
    cached: bool = False


class MarketTrendItem(BaseModel):
    symbol: str
    name: str
    price: float
    change: float | None = None
    change_percent: float | None = None
    currency: str = "KRW"


class MarketTrendsResponse(BaseModel):
    indices: list[MarketTrendItem]
    gainers: list[MarketTrendItem]
    losers: list[MarketTrendItem]
    cached: bool = False


class MarketSearchResult(BaseModel):
    symbol: str
    name: str
    exchange: str | None = None
    asset_type: str | None = None


class MarketSearchResponse(BaseModel):
    query: str
    results: list[MarketSearchResult]
    cached: bool = False
