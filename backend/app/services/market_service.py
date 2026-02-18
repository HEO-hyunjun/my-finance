import asyncio
import hashlib
import json
import logging

import httpx
import redis.asyncio as redis

from app.core.config import settings
from app.models.asset import AssetType
from app.schemas.market import (
    PriceResponse, ExchangeRateResponse,
    MarketTrendItem, MarketTrendsResponse,
    MarketSearchResult, MarketSearchResponse,
)

logger = logging.getLogger(__name__)

CACHE_TTL = 300  # 시세 캐시 5분
KRX_GOLD_CACHE_TTL = 600  # KRX 금 시세 캐시 10분

# yfinance 티커 변환: asset_type → suffix
YF_SUFFIX_MAP = {
    AssetType.STOCK_KR: ".KS",
    AssetType.STOCK_US: "",
    AssetType.GOLD: "",
}

# 주요 지수 티커 (yfinance)
MARKET_INDEX_TICKERS = [
    ("^KS11", "코스피", "KRW"),
    ("^KQ11", "코스닥", "KRW"),
    ("^GSPC", "S&P 500", "USD"),
    ("^DJI", "다우존스", "USD"),
    ("^IXIC", "나스닥", "USD"),
]


def _to_yf_ticker(symbol: str, asset_type: AssetType | None = None) -> str:
    """종목 코드를 yfinance 티커 형식으로 변환"""
    if asset_type == AssetType.GOLD:
        return "GC=F"
    suffix = YF_SUFFIX_MAP.get(asset_type, "") if asset_type else ""
    return f"{symbol}{suffix}"


def _fetch_yf_price(ticker_symbol: str) -> dict:
    """yfinance로 시세 조회 (동기 - thread에서 실행)"""
    import yfinance as yf

    ticker = yf.Ticker(ticker_symbol)
    info = ticker.info

    return {
        "name": info.get("shortName") or info.get("longName") or ticker_symbol,
        "price": info.get("currentPrice") or info.get("regularMarketPrice") or 0,
        "currency": info.get("currency", "USD"),
        "price_change": info.get("regularMarketChange"),
        "price_change_percentage": info.get("regularMarketChangePercent"),
        "is_market_open": info.get("marketState") == "REGULAR",
    }


def _fetch_yf_indices() -> list[dict]:
    """yfinance로 주요 지수 일괄 조회 (동기 - thread에서 실행)"""
    import yfinance as yf

    tickers = yf.Tickers(" ".join(t[0] for t in MARKET_INDEX_TICKERS))
    results = []

    for symbol, name, currency in MARKET_INDEX_TICKERS:
        try:
            info = tickers.tickers[symbol].info
            results.append({
                "symbol": symbol,
                "name": name,
                "price": info.get("regularMarketPrice", 0),
                "change": info.get("regularMarketChange", 0),
                "change_percent": info.get("regularMarketChangePercent", 0),
                "currency": currency,
            })
        except Exception:
            logger.warning(f"Failed to fetch index: {symbol}")
    return results


def _search_yf_tickers(query: str) -> list[dict]:
    """Yahoo Finance 검색 API로 종목 검색 (동기 - thread에서 실행)"""
    import yfinance as yf

    try:
        results = yf.search(query, max_results=10)
        quotes = results.get("quotes", []) if isinstance(results, dict) else []
        return [
            {
                "symbol": q.get("symbol", ""),
                "name": q.get("shortname") or q.get("longname", ""),
                "exchange": q.get("exchange"),
            }
            for q in quotes
            if q.get("symbol")
        ]
    except Exception:
        # yfinance.search가 없는 버전이면 httpx로 직접 호출
        try:
            with httpx.Client(timeout=10.0) as client:
                resp = client.get(
                    "https://query2.finance.yahoo.com/v1/finance/search",
                    params={"q": query, "quotesCount": 10, "lang": "ko-KR"},
                    headers={"User-Agent": "Mozilla/5.0"},
                )
                resp.raise_for_status()
                data = resp.json()
            return [
                {
                    "symbol": q.get("symbol", ""),
                    "name": q.get("shortname") or q.get("longname", ""),
                    "exchange": q.get("exchange"),
                }
                for q in data.get("quotes", [])
                if q.get("symbol")
            ]
        except Exception:
            logger.warning(f"Yahoo search failed for: {query}")
            return []


def _fetch_krx_gold_price() -> dict:
    """KRX 금시장 매매기준가격 조회 (동기 - thread에서 실행)

    네이버 금융에서 KRX 금 현물 매매기준가격(KRW/g)을 가져온다.
    """
    import re
    import urllib.request

    url = "https://finance.naver.com/marketindex/goldDailyQuote.naver?page=1"
    req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})

    with urllib.request.urlopen(req, timeout=10) as resp:
        html = resp.read().decode("euc-kr", errors="replace")

    # 첫 번째 데이터 행: 날짜, 매매기준가격(KRW/g), 전일대비, 등락방향
    rows = re.findall(
        r'<tr class="(up|down)">\s*'
        r'<td class="date">([\d.]+)</td>\s*'
        r'<td class="num">([\d,\.]+)</td>\s*'  # 매매기준가격
        r'<td class="num">.*?([\d,\.]+)</td>',  # 전일대비
        html,
        re.DOTALL,
    )

    if not rows:
        raise ValueError("Failed to parse Naver gold price page")

    direction, trade_date, price_str, change_str = rows[0]

    price = float(price_str.replace(",", ""))
    change = float(change_str.replace(",", ""))
    if direction == "down":
        change = -change

    change_pct = (change / (price - change) * 100) if (price - change) > 0 else 0

    return {
        "symbol": "KRX:GOLD",
        "name": "금 (KRX)",
        "price": price,
        "currency": "KRW",
        "change": change,
        "change_percent": round(change_pct, 2),
    }


class MarketService:
    def __init__(self, redis_client: redis.Redis):
        self._redis = redis_client

    # ─── 시세 (yfinance) ────────────────────────

    async def get_price(
        self, symbol: str, asset_type: AssetType | None = None
    ) -> PriceResponse:
        # KRX 금 현물은 전용 조회 사용
        if symbol == "KRX:GOLD" or (asset_type == AssetType.GOLD and symbol in ("KRX:GOLD", "")):
            return await self.get_krx_gold_price()

        ticker_symbol = _to_yf_ticker(symbol, asset_type)
        cache_key = f"market:price:{ticker_symbol}"

        cached = await self._get_cached(cache_key)
        if cached:
            cached.pop("cached", None)
            return PriceResponse(**cached, cached=True)

        try:
            data = await asyncio.to_thread(_fetch_yf_price, ticker_symbol)
        except Exception:
            logger.warning(f"yfinance failed for {ticker_symbol}, using mock")
            data = self._mock_data(symbol)

        response = PriceResponse(
            symbol=symbol,
            name=data.get("name"),
            price=float(data.get("price", 0)),
            currency=data.get("currency", "USD"),
            change=data.get("price_change"),
            change_percent=data.get("price_change_percentage"),
            is_market_open=data.get("is_market_open", True),
            cached=False,
        )

        await self._set_cached(cache_key, response.model_dump(), CACHE_TTL)
        return response

    async def get_exchange_rate(self) -> ExchangeRateResponse:
        cache_key = "market:exchange_rate:USDKRW"

        cached = await self._get_cached(cache_key)
        if cached:
            cached.pop("cached", None)
            return ExchangeRateResponse(**cached, cached=True)

        try:
            data = await asyncio.to_thread(_fetch_yf_price, "USDKRW=X")
        except Exception:
            logger.warning("yfinance exchange rate failed, using mock")
            data = {"price": 1380.0, "currency": "KRW", "name": "USD/KRW"}

        response = ExchangeRateResponse(
            pair="USD/KRW",
            rate=float(data.get("price", 0)),
            change=data.get("price_change"),
            change_percent=data.get("price_change_percentage"),
            cached=False,
        )

        await self._set_cached(cache_key, response.model_dump(), CACHE_TTL)
        return response

    async def get_market_trends(self) -> MarketTrendsResponse:
        cache_key = "market:trends"

        cached = await self._get_cached(cache_key)
        if cached:
            cached.pop("cached", None)
            return MarketTrendsResponse(**cached, cached=True)

        try:
            raw_indices = await asyncio.to_thread(_fetch_yf_indices)
        except Exception:
            logger.warning("yfinance market trends failed, using mock")
            return MarketTrendsResponse(
                indices=[
                    MarketTrendItem(symbol="KOSPI", name="코스피", price=2650.0, change=15.0, change_percent=0.57),
                    MarketTrendItem(symbol="KOSDAQ", name="코스닥", price=870.0, change=-3.0, change_percent=-0.34),
                    MarketTrendItem(symbol="S&P500", name="S&P 500", price=6100.0, change=25.0, change_percent=0.41, currency="USD"),
                ],
                gainers=[], losers=[], cached=False,
            )

        indices = [
            MarketTrendItem(
                symbol=item["symbol"],
                name=item["name"],
                price=float(item.get("price", 0)),
                change=float(item.get("change", 0)),
                change_percent=float(item.get("change_percent", 0)),
                currency=item.get("currency", "KRW"),
            )
            for item in raw_indices
        ]

        response = MarketTrendsResponse(indices=indices, gainers=[], losers=[], cached=False)
        await self._set_cached(cache_key, response.model_dump(), CACHE_TTL)
        return response

    async def search_market(self, query: str) -> MarketSearchResponse:
        cache_key = f"market:search:{query}"

        cached = await self._get_cached(cache_key)
        if cached:
            cached.pop("cached", None)
            return MarketSearchResponse(**cached, cached=True)

        try:
            raw_results = await asyncio.to_thread(_search_yf_tickers, query)
        except Exception:
            logger.warning(f"Yahoo search failed for: {query}")
            raw_results = []

        results = [
            MarketSearchResult(
                symbol=item["symbol"],
                name=item["name"],
                exchange=item.get("exchange"),
            )
            for item in raw_results
        ]

        # 금 관련 검색어면 KRX 금 현물을 결과 맨 앞에 추가
        gold_keywords = {"금", "gold", "골드", "krx gold", "krx:gold", "금현물"}
        if query.strip().lower() in gold_keywords:
            krx_gold = MarketSearchResult(
                symbol="KRX:GOLD",
                name="금 현물 (KRX)",
                exchange="KRX",
            )
            results.insert(0, krx_gold)

        response = MarketSearchResponse(query=query, results=results, cached=False)
        await self._set_cached(cache_key, response.model_dump(), 600)
        return response

    # ─── KRX 금시장 ────────────────────────────

    async def get_krx_gold_price(self) -> PriceResponse:
        """KRX 금시장 금 현물 시세 조회 (KRW/g)"""
        cache_key = "market:krx_gold"

        cached = await self._get_cached(cache_key)
        if cached:
            cached.pop("cached", None)
            return PriceResponse(**cached, cached=True)

        try:
            data = await asyncio.to_thread(_fetch_krx_gold_price)
        except Exception:
            logger.warning("KRX gold price fetch failed, falling back to yfinance GC=F")
            try:
                data = await asyncio.to_thread(_fetch_yf_price, "GC=F")
                data["symbol"] = "GC=F"
                data["name"] = "금 (COMEX)"
            except Exception:
                logger.warning("yfinance GC=F also failed, using mock")
                data = {
                    "symbol": "KRX:GOLD",
                    "name": "금 (KRX)",
                    "price": 0,
                    "currency": "KRW",
                    "change": None,
                    "change_percent": None,
                }

        response = PriceResponse(
            symbol=data.get("symbol", "KRX:GOLD"),
            name=data.get("name", "금 (KRX)"),
            price=float(data.get("price", 0)),
            currency=data.get("currency", "KRW"),
            change=data.get("change") or data.get("price_change"),
            change_percent=data.get("change_percent") or data.get("price_change_percentage"),
            is_market_open=data.get("is_market_open", True),
            cached=False,
        )

        await self._set_cached(cache_key, response.model_dump(), KRX_GOLD_CACHE_TTL)
        return response

    # ─── 웹 검색 (SerpAPI / Firecrawl 분기) + 쿼터 관리 ─────

    async def _check_serpapi_quota(self) -> bool:
        """SerpAPI 쿼터 확인 (news_service와 동일한 Redis 카운터 공유)"""
        from datetime import date as date_type

        today = date_type.today().isoformat()
        month = date_type.today().strftime("%Y-%m")

        try:
            daily = await self._redis.get(f"serpapi:quota:daily:{today}")
            monthly = await self._redis.get(f"serpapi:quota:monthly:{month}")

            daily_count = int(daily) if daily else 0
            monthly_count = int(monthly) if monthly else 0

            return (
                daily_count < settings.SERPAPI_DAILY_LIMIT
                and monthly_count < settings.SERPAPI_MONTHLY_LIMIT
            )
        except Exception:
            return False

    async def _increment_serpapi_quota(self):
        """SerpAPI 호출 카운터 증가"""
        from datetime import date as date_type

        today = date_type.today().isoformat()
        month = date_type.today().strftime("%Y-%m")

        try:
            pipe = self._redis.pipeline()
            pipe.incr(f"serpapi:quota:daily:{today}")
            pipe.expire(f"serpapi:quota:daily:{today}", 172800)
            pipe.incr(f"serpapi:quota:monthly:{month}")
            pipe.expire(f"serpapi:quota:monthly:{month}", 3024000)
            await pipe.execute()
        except Exception as e:
            logger.warning(f"Quota increment failed: {e}")

    async def web_search(self, query: str, num_results: int = 5) -> list[dict]:
        """웹 검색 - 쿼터 확인 후 SerpAPI 또는 Firecrawl 사용 (캐시 2시간)"""
        cache_key = f"web_search:{hashlib.md5(query.encode()).hexdigest()}"
        cached = await self._get_cached(cache_key)
        if cached:
            return cached

        # 쿼터 확인 (SerpAPI 프로바이더일 경우)
        if settings.SEARCH_PROVIDER != "firecrawl":
            if not await self._check_serpapi_quota():
                logger.info(f"SerpAPI quota exceeded for web_search: '{query}'")
                return []

        if settings.SEARCH_PROVIDER == "firecrawl":
            results = await self._web_search_firecrawl(query, num_results)
        else:
            results = await self._web_search_serpapi(query, num_results)
            if results:
                await self._increment_serpapi_quota()

        if results:
            await self._set_cached(cache_key, results, settings.WEB_SEARCH_CACHE_TTL)
        return results

    async def _web_search_serpapi(self, query: str, num_results: int) -> list[dict]:
        if not settings.SERPAPI_KEY:
            return []

        params = {
            "engine": "google",
            "q": query,
            "num": num_results,
            "hl": "ko",
            "api_key": settings.SERPAPI_KEY,
        }

        try:
            async with httpx.AsyncClient(timeout=10.0) as client:
                resp = await client.get("https://serpapi.com/search", params=params)
                resp.raise_for_status()
                result = resp.json()

            return [
                {
                    "title": r.get("title", ""),
                    "link": r.get("link", ""),
                    "snippet": r.get("snippet", ""),
                }
                for r in result.get("organic_results", [])[:num_results]
            ]
        except Exception:
            logger.warning(f"SerpAPI web search failed for: {query}")
            return []

    async def _web_search_firecrawl(self, query: str, num_results: int) -> list[dict]:
        if not settings.FIRECRAWL_API_KEY:
            logger.warning("FIRECRAWL_API_KEY not set")
            return []

        try:
            from firecrawl import FirecrawlApp
            fc_kwargs = {"api_key": settings.FIRECRAWL_API_KEY}
            if settings.FIRECRAWL_BASE_URL:
                fc_kwargs["api_url"] = settings.FIRECRAWL_BASE_URL
            app = FirecrawlApp(**fc_kwargs)
            results = await asyncio.to_thread(
                app.search, query, {"limit": num_results}
            )

            return [
                {
                    "title": r.get("title", ""),
                    "link": r.get("url", ""),
                    "snippet": r.get("description", "") or r.get("markdown", "")[:200],
                }
                for r in (results.get("data", []) if isinstance(results, dict) else results)
            ]
        except Exception as e:
            logger.warning(f"Firecrawl web search failed: {e}")
            return []

    # ─── 유틸 ───────────────────────────────────

    def _mock_data(self, query: str) -> dict:
        if "USD-KRW" in query:
            return {"price": 1380.0, "currency": "KRW", "name": "USD/KRW"}
        return {"price": 100.0, "currency": "KRW", "name": query}

    async def _get_cached(self, key: str) -> dict | None:
        try:
            data = await self._redis.get(key)
            if data:
                return json.loads(data)
        except Exception:
            logger.warning(f"Redis cache read failed for {key}")
        return None

    async def _set_cached(self, key: str, data: dict, ttl: int) -> None:
        try:
            await self._redis.set(key, json.dumps(data), ex=ttl)
        except Exception:
            logger.warning(f"Redis cache write failed for {key}")
