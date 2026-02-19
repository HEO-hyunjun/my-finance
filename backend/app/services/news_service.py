import hashlib
import json
import logging
from datetime import date, datetime, timezone

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
    """뉴스 검색 서비스 - DB-first + SearchProvider 인터페이스"""

    def __init__(self, redis_client: redis.Redis):
        self._redis = redis_client

    # ─── 뉴스 검색 (DB-first) ───────────────────

    async def search_news(
        self,
        query: str,
        page: int = 1,
        per_page: int = 20,
        category: str = NewsCategory.ALL,
        related_asset: str | None = None,
    ) -> NewsListResponse:
        """뉴스 검색: Redis 캐시 → DB 조회 → SearchProvider"""
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

        # 3. SearchProvider 검색
        raw_articles = await self._fetch_news(query)

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

    async def get_my_asset_news(
        self,
        asset_names: list[str],
        max_per_asset: int = 3,
    ) -> MyAssetNewsResponse:
        """보유 자산별 뉴스 - DB에서 키워드 검색 (API 호출 없음!)"""
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
        """검색 결과를 DB에 저장"""
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
                    source=NewsSource(name=item.get("source_name", ""), icon=None),
                    snippet=item.get("summary") or item.get("snippet"),
                    thumbnail=item.get("thumbnail"),
                    published_at=item.get("published_at", ""),
                    category=category,
                    related_asset=related_asset,
                )
            )
        return articles

    # ─── SearchProvider 연동 ─────────────────────

    async def _fetch_news(self, query: str) -> list[dict]:
        """SearchProvider를 통해 뉴스 검색"""
        from app.services.search import get_search_provider

        provider = get_search_provider()
        return await provider.search_news(query)

    # ─── 매핑 / 유틸 ─────────────────────────────

    def _map_articles(
        self,
        raw: list[dict],
        category: str,
        related_asset: str | None = None,
    ) -> list[NewsArticle]:
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
