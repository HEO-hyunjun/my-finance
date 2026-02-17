import asyncio
import hashlib
import json
import logging
from datetime import date, datetime, timezone

import httpx
import redis.asyncio as redis

from app.core.config import settings
from app.schemas.news import (
    CATEGORY_QUERY_MAP,
    MyAssetNewsResponse,
    NewsArticle,
    NewsCategory,
    NewsListResponse,
    NewsSource,
)

logger = logging.getLogger(__name__)


class NewsService:
    """뉴스 검색 서비스 - DB-first + SerpAPI 쿼터 관리"""

    def __init__(self, redis_client: redis.Redis):
        self._redis = redis_client

    # ─── 쿼터 관리 (Redis 카운터) ────────────────

    async def _check_quota(self) -> bool:
        """SerpAPI 일일/월간 쿼터 확인"""
        today = date.today().isoformat()
        month = date.today().strftime("%Y-%m")

        daily_key = f"serpapi:quota:daily:{today}"
        monthly_key = f"serpapi:quota:monthly:{month}"

        try:
            daily = await self._redis.get(daily_key)
            monthly = await self._redis.get(monthly_key)

            daily_count = int(daily) if daily else 0
            monthly_count = int(monthly) if monthly else 0

            within_limit = (
                daily_count < settings.SERPAPI_DAILY_LIMIT
                and monthly_count < settings.SERPAPI_MONTHLY_LIMIT
            )
            if not within_limit:
                logger.info(
                    f"SerpAPI quota exceeded: daily={daily_count}/{settings.SERPAPI_DAILY_LIMIT}, "
                    f"monthly={monthly_count}/{settings.SERPAPI_MONTHLY_LIMIT}"
                )
            return within_limit
        except Exception as e:
            logger.warning(f"Quota check failed: {e}")
            return False

    async def _increment_quota(self):
        """SerpAPI 호출 카운터 증가"""
        today = date.today().isoformat()
        month = date.today().strftime("%Y-%m")

        daily_key = f"serpapi:quota:daily:{today}"
        monthly_key = f"serpapi:quota:monthly:{month}"

        try:
            pipe = self._redis.pipeline()
            pipe.incr(daily_key)
            pipe.expire(daily_key, 172800)    # 48시간
            pipe.incr(monthly_key)
            pipe.expire(monthly_key, 3024000)  # 35일
            await pipe.execute()
        except Exception as e:
            logger.warning(f"Quota increment failed: {e}")

    # ─── 뉴스 검색 (DB-first) ───────────────────

    async def search_news(
        self,
        query: str,
        page: int = 1,
        per_page: int = 20,
        category: str = NewsCategory.ALL,
        related_asset: str | None = None,
    ) -> NewsListResponse:
        """뉴스 검색: Redis 캐시 → DB 조회 → SerpAPI (쿼터 확인)"""
        cache_key = self._cache_key(query, page)

        # 1. Redis 캐시 확인 (12시간 TTL)
        cached = await self._get_cached(cache_key)
        if cached:
            return NewsListResponse(**cached)

        # 2. DB 조회 (최근 12시간 기사)
        db_results = await self._search_from_db(query)
        if db_results:
            articles = self._map_db_results(db_results, category, related_asset)
            start = (page - 1) * per_page
            end = start + per_page
            page_articles = articles[start:end]

            result = NewsListResponse(
                articles=page_articles,
                page=page,
                per_page=per_page,
                has_next=end < len(articles),
            )
            await self._set_cached(cache_key, result.model_dump(), settings.NEWS_CACHE_TTL)
            return result

        # 3. 쿼터 확인 후 SerpAPI 호출
        if await self._check_quota():
            raw_articles = await self._fetch_news(query)
            await self._increment_quota()

            # DB에도 저장
            await self._save_fetched_to_db(raw_articles, category, related_asset)

            articles = self._map_articles(raw_articles, category, related_asset)
            start = (page - 1) * per_page
            end = start + per_page
            page_articles = articles[start:end]

            result = NewsListResponse(
                articles=page_articles,
                page=page,
                per_page=per_page,
                has_next=end < len(articles),
            )
            await self._set_cached(cache_key, result.model_dump(), settings.NEWS_CACHE_TTL)
            return result

        # 4. 쿼터 초과 → 빈 결과 반환 (에러 아님)
        logger.info(f"Quota exceeded, returning empty result for '{query}'")
        return NewsListResponse(articles=[], page=page, per_page=per_page, has_next=False)

    async def get_my_asset_news(
        self,
        asset_names: list[str],
        max_per_asset: int = 3,
    ) -> MyAssetNewsResponse:
        """보유 자산별 뉴스 - DB에서 키워드 검색 (SerpAPI 호출 없음!)"""
        queries = asset_names[:5]

        try:
            from app.core.database import AsyncSessionLocal
            from app.services.news_llm_service import search_articles_by_keywords

            async with AsyncSessionLocal() as db:
                db_results = await search_articles_by_keywords(
                    db, queries, hours=24, limit=max_per_asset * len(queries)
                )

            all_articles: list[NewsArticle] = []
            seen_ids: set[str] = set()

            for item in db_results:
                ext_id = item.get("external_id", "")
                if ext_id in seen_ids:
                    continue
                seen_ids.add(ext_id)

                # DB에서 어떤 자산 키워드와 매칭되는지 찾기
                matched_asset = None
                title_lower = (item.get("title") or "").lower()
                snippet_lower = (item.get("snippet") or "").lower()
                for q in queries:
                    if q.lower() in title_lower or q.lower() in snippet_lower:
                        matched_asset = q
                        break

                all_articles.append(
                    NewsArticle(
                        id=ext_id,
                        title=item.get("title", ""),
                        link=item.get("link", ""),
                        source=NewsSource(name=item.get("source_name", ""), icon=None),
                        snippet=item.get("summary") or item.get("snippet"),
                        thumbnail=item.get("thumbnail"),
                        published_at=item.get("published_at", ""),
                        category=NewsCategory.MY_ASSETS,
                        related_asset=matched_asset,
                    )
                )

            return MyAssetNewsResponse(articles=all_articles, asset_queries=queries)

        except Exception as e:
            logger.warning(f"DB asset news search failed: {e}")
            return MyAssetNewsResponse(articles=[], asset_queries=queries)

    # ─── DB 검색 ─────────────────────────────────

    async def _search_from_db(self, query: str) -> list[dict]:
        """DB에서 최근 12시간 기사 검색"""
        try:
            from app.core.database import AsyncSessionLocal
            from app.services.news_llm_service import search_articles_by_keywords

            async with AsyncSessionLocal() as db:
                results = await search_articles_by_keywords(
                    db, [query], hours=12, limit=20
                )
            return results
        except Exception as e:
            logger.warning(f"DB search failed for '{query}': {e}")
            return []

    async def _save_fetched_to_db(
        self, raw_articles: list[dict], category: str, related_asset: str | None
    ):
        """SerpAPI 결과를 DB에 저장"""
        try:
            from app.core.database import AsyncSessionLocal
            from app.services.news_llm_service import save_articles_to_db

            articles = self._map_articles(raw_articles, category, related_asset)
            if articles:
                async with AsyncSessionLocal() as db:
                    await save_articles_to_db(db, articles)
        except Exception as e:
            logger.warning(f"Failed to save fetched articles to DB: {e}")

    # ─── DB 결과 → NewsArticle 변환 ────────────

    def _map_db_results(
        self,
        db_results: list[dict],
        category: str,
        related_asset: str | None = None,
    ) -> list[NewsArticle]:
        """DB 조회 결과(dict) → NewsArticle 목록 변환"""
        articles: list[NewsArticle] = []
        for item in db_results:
            title = item.get("title", "")
            link = item.get("link", "")
            if not title or not link:
                continue
            articles.append(
                NewsArticle(
                    id=item.get("external_id") or NewsArticle.generate_id(title, link),
                    title=title,
                    link=link,
                    source=NewsSource(
                        name=item.get("source_name", ""),
                        icon=None,
                    ),
                    snippet=item.get("summary") or item.get("snippet"),
                    thumbnail=item.get("thumbnail"),
                    published_at=item.get("published_at", ""),
                    category=category,
                    related_asset=related_asset,
                )
            )
        return articles

    # ─── 뉴스 검색 분기 (SerpAPI / Firecrawl) ───

    async def _fetch_news(self, query: str) -> list[dict]:
        """SEARCH_PROVIDER에 따라 뉴스 검색 분기"""
        if settings.SEARCH_PROVIDER == "firecrawl":
            return await self._fetch_firecrawl_news(query)
        return await self._fetch_serpapi_news(query)

    async def _fetch_serpapi_news(self, query: str) -> list[dict]:
        """SerpAPI google_news 엔진 호출"""
        if not settings.SERPAPI_KEY:
            logger.warning("SERPAPI_KEY not set, returning mock news")
            return self._mock_news(query)

        params = {
            "engine": "google_news",
            "q": query,
            "gl": "kr",
            "hl": "ko",
            "api_key": settings.SERPAPI_KEY,
        }

        async with httpx.AsyncClient(timeout=10.0) as client:
            resp = await client.get("https://serpapi.com/search", params=params)
            resp.raise_for_status()
            data = resp.json()

        return data.get("news_results", [])

    async def _fetch_firecrawl_news(self, query: str) -> list[dict]:
        """Firecrawl search로 뉴스 검색"""
        if not settings.FIRECRAWL_API_KEY:
            logger.warning("FIRECRAWL_API_KEY not set, returning mock news")
            return self._mock_news(query)

        try:
            from firecrawl import FirecrawlApp
            fc_kwargs = {"api_key": settings.FIRECRAWL_API_KEY}
            if settings.FIRECRAWL_BASE_URL:
                fc_kwargs["api_url"] = settings.FIRECRAWL_BASE_URL
            app = FirecrawlApp(**fc_kwargs)

            # 뉴스 키워드 추가하여 뉴스 결과 우선
            news_query = f"{query} 뉴스 최신"
            results = await asyncio.to_thread(
                app.search, news_query, {"limit": 20}
            )

            raw_data = results.get("data", []) if isinstance(results, dict) else results

            # Firecrawl 결과를 SerpAPI 형식으로 변환
            return [
                {
                    "title": r.get("title", ""),
                    "link": r.get("url", ""),
                    "source": {"name": self._extract_domain(r.get("url", "")), "icon": None},
                    "snippet": r.get("description", "") or (r.get("markdown", "") or "")[:200],
                    "thumbnail": None,
                    "date": "",
                }
                for r in raw_data
                if r.get("title") and r.get("url")
            ]
        except Exception as e:
            logger.warning(f"Firecrawl news search failed: {e}")
            return self._mock_news(query)

    # ─── 매핑 / 유틸 ─────────────────────────────

    def _map_articles(
        self,
        raw: list[dict],
        category: str,
        related_asset: str | None = None,
    ) -> list[NewsArticle]:
        """검색 결과 → NewsArticle 목록 매핑"""
        articles: list[NewsArticle] = []
        for item in raw:
            title = item.get("title", "")
            link = item.get("link", "")
            if not title or not link:
                continue

            source_data = item.get("source", {})
            articles.append(
                NewsArticle(
                    id=NewsArticle.generate_id(title, link),
                    title=title,
                    link=link,
                    source=NewsSource(
                        name=source_data.get("name", ""),
                        icon=source_data.get("icon"),
                    ),
                    snippet=item.get("snippet"),
                    thumbnail=item.get("thumbnail"),
                    published_at=item.get("date", ""),
                    category=category,
                    related_asset=related_asset,
                )
            )
        return articles

    @staticmethod
    def _extract_domain(url: str) -> str:
        """URL에서 도메인명 추출"""
        try:
            from urllib.parse import urlparse
            parsed = urlparse(url)
            domain = parsed.netloc.replace("www.", "")
            return domain
        except Exception:
            return ""

    def _mock_news(self, query: str) -> list[dict]:
        """API 키 미설정 시 더미 뉴스 반환"""
        return [
            {
                "title": f"[Mock] {query} 관련 뉴스 {i}",
                "link": f"https://example.com/news/{query}/{i}",
                "source": {"name": "Mock News", "icon": None},
                "snippet": f"{query}에 대한 최신 뉴스입니다. (Mock 데이터)",
                "thumbnail": None,
                "date": f"{i}시간 전",
            }
            for i in range(1, 6)
        ]

    def _cache_key(self, query: str, page: int) -> str:
        query_hash = hashlib.md5(query.encode()).hexdigest()[:8]
        return f"news:{query_hash}:{page}"

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
            await self._redis.set(key, json.dumps(data, default=str), ex=ttl)
        except Exception:
            logger.warning(f"Redis cache write failed for {key}")
