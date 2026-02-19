"""뉴스 서비스 - RDB-primary + Redis 캐시 아키텍처.

Flow:
  1. 사용자 요청 → Redis 캐시 확인 (7h TTL)
  2. Redis hit → 즉시 반환
  3. Redis miss → DB에서 최근 7시간 기사 조회
  4. DB hit → Redis에 캐시 후 반환
  5. DB miss → API(Tavily) fetch → DB 저장 → Redis 캐시 → 반환
  6. 서버 재시작 시 DB에서 Redis 워밍
"""

import hashlib
import json
import logging
from datetime import datetime, timezone

import redis.asyncio as redis

from app.core.config import settings
from app.schemas.news import (
    CATEGORY_QUERY_MAP,
    MyAssetNewsResponse,
    NewsArticle,
    NewsCategory,
    NewsListResponse,
    NewsSource,
    build_batch_query,
    classify_article_category,
    filter_asset_names,
)

logger = logging.getLogger(__name__)

# Redis 캐시 키 prefix
_CACHE_PREFIX = "news"
_CACHE_ALL_KEY = f"{_CACHE_PREFIX}:all"  # 전체 뉴스 캐시
_CACHE_WARMED_KEY = f"{_CACHE_PREFIX}:warmed"  # 워밍 완료 플래그


class NewsService:
    """뉴스 검색 서비스 - RDB-primary + Redis 캐시"""

    def __init__(self, redis_client: redis.Redis):
        self._redis = redis_client

    # ─── 뉴스 검색 (사용자 요청) ──────────────

    async def search_news(
        self,
        query: str,
        page: int = 1,
        per_page: int = 20,
        category: str = NewsCategory.ALL,
        related_asset: str | None = None,
    ) -> NewsListResponse:
        """카테고리/검색어 기반 뉴스 조회"""
        cache_key = self._cache_key(category, query, page)

        # 1. Redis 캐시 확인
        cached = await self._get_cached(cache_key)
        if cached:
            return NewsListResponse(**cached)

        # 2. DB에서 최근 7시간 기사 조회
        articles = await self._load_from_db(category=category, query=query)

        # 3. DB에 데이터 없으면 API fetch → DB 저장
        if not articles:
            articles = await self._fetch_and_save(query, category)

        # 4. 페이지네이션 + 캐시
        start = (page - 1) * per_page
        end = start + per_page
        page_articles = articles[start:end]

        result = NewsListResponse(
            articles=page_articles,
            page=page,
            per_page=per_page,
            has_next=end < len(articles),
        )
        await self._set_cached(cache_key, result.model_dump())
        return result

    async def get_my_asset_news(
        self,
        asset_names: list[str],
        max_per_asset: int = 3,
    ) -> MyAssetNewsResponse:
        """보유 자산별 뉴스 - DB 우선, 부족 시 API 폴백"""
        queries = filter_asset_names(asset_names)[:5]

        if not queries:
            return MyAssetNewsResponse(articles=[], asset_queries=[])

        cache_key = self._cache_key("my_assets", ",".join(sorted(queries)))
        cached = await self._get_cached(cache_key)
        if cached:
            return MyAssetNewsResponse(**cached)

        all_articles: list[NewsArticle] = []
        seen_ids: set[str] = set()

        # 1. DB 검색 시도
        try:
            from app.core.database import async_session as AsyncSessionLocal
            from app.services.news_llm_service import search_articles_by_keywords

            async with AsyncSessionLocal() as db:
                db_results = await search_articles_by_keywords(
                    db, queries, hours=settings.NEWS_CACHE_TTL // 3600, limit=max_per_asset * len(queries)
                )

            for item in db_results:
                ext_id = item.get("external_id", "")
                if ext_id in seen_ids:
                    continue
                seen_ids.add(ext_id)

                matched_asset = self._match_asset(item, queries)
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
        except Exception as e:
            logger.warning(f"DB asset news search failed: {e}")

        # 2. DB 결과 부족 시 API 폴백
        if len(all_articles) < 3:
            try:
                query = " OR ".join(queries) + " 주가 뉴스"
                raw = await self._fetch_news(query)

                # DB에도 저장
                await self._save_raw_to_db(raw, NewsCategory.MY_ASSETS)

                for item in raw:
                    title = item.get("title", "")
                    link = item.get("link", "")
                    if not title or not link:
                        continue
                    art_id = NewsArticle.generate_id(title, link)
                    if art_id in seen_ids:
                        continue
                    seen_ids.add(art_id)

                    matched_asset = self._match_asset(item, queries)
                    all_articles.append(
                        NewsArticle(
                            id=art_id,
                            title=title,
                            link=link,
                            source=NewsSource(
                                name=item.get("source", {}).get("name", "") if isinstance(item.get("source"), dict) else str(item.get("source", "")),
                                icon=None,
                            ),
                            snippet=(item.get("snippet") or "")[:300],
                            thumbnail=item.get("thumbnail"),
                            published_at=item.get("date", ""),
                            category=NewsCategory.MY_ASSETS,
                            related_asset=matched_asset,
                        )
                    )
            except Exception as e:
                logger.warning(f"API asset news fallback failed: {e}")

        result = MyAssetNewsResponse(articles=all_articles, asset_queries=queries)
        await self._set_cached(cache_key, result.model_dump())
        return result

    # ─── 배치 수집 (Celery task에서 호출) ─────

    async def collect_and_cache_all(self, asset_names: list[str] | None = None) -> dict:
        """전체 뉴스 배치 수집 → DB 저장 → Redis 캐시.

        Celery beat에서 주기적으로 호출되며,
        최대 2개 API 호출로 일반 경제 + 보유 자산 뉴스를 수집합니다.
        """
        total_fetched = 0
        total_saved = 0
        all_articles: list[NewsArticle] = []
        seen_ids: set[str] = set()

        # API 호출 최소화: 최대 2개 쿼리
        queries = [CATEGORY_QUERY_MAP[NewsCategory.ALL]]  # 1) 일반 경제 뉴스
        asset_query = build_batch_query(asset_names)
        if asset_query != CATEGORY_QUERY_MAP[NewsCategory.ALL]:
            queries.append(asset_query)  # 2) 보유 자산 뉴스

        for query in queries:
            try:
                raw = await self._fetch_news(query)
                total_fetched += len(raw)

                for item in raw:
                    title = item.get("title", "")
                    link = item.get("link", "")
                    if not title or not link:
                        continue

                    art_id = NewsArticle.generate_id(title, link)
                    if art_id in seen_ids:
                        continue
                    seen_ids.add(art_id)

                    category = classify_article_category(title, item.get("snippet"))
                    source_data = item.get("source", {})
                    all_articles.append(
                        NewsArticle(
                            id=art_id,
                            title=title,
                            link=link,
                            source=NewsSource(
                                name=source_data.get("name", "") if isinstance(source_data, dict) else str(source_data),
                                icon=source_data.get("icon") if isinstance(source_data, dict) else None,
                            ),
                            snippet=(item.get("snippet") or item.get("content", ""))[:300],
                            thumbnail=item.get("thumbnail"),
                            published_at=item.get("date", ""),
                            category=category,
                            related_asset=None,
                        )
                    )
            except Exception as e:
                logger.warning(f"Batch fetch failed for query '{query}': {e}")

        # DB에 저장
        if all_articles:
            try:
                from app.core.database import async_session as AsyncSessionLocal
                from app.services.news_llm_service import save_articles_to_db

                async with AsyncSessionLocal() as db:
                    total_saved = await save_articles_to_db(db, all_articles)
            except Exception as e:
                logger.warning(f"Batch DB save failed: {e}")

        # Redis 캐시 워밍 (카테고리별)
        await self._warm_cache_from_articles(all_articles)

        logger.info(f"Batch collect: {total_fetched} fetched, {len(all_articles)} unique, {total_saved} saved to DB")
        return {"total_fetched": total_fetched, "unique": len(all_articles), "saved": total_saved}

    # ─── 서버 시작 시 Redis 워밍 ─────────────

    async def warm_cache_from_db(self) -> int:
        """서버 시작 시 DB에서 최근 7시간 기사를 Redis로 로드.

        이미 워밍된 경우 스킵.
        """
        # 이미 워밍 완료 체크
        try:
            warmed = await self._redis.get(_CACHE_WARMED_KEY)
            if warmed:
                logger.info("Redis cache already warmed, skipping")
                return 0
        except Exception:
            pass

        try:
            from app.core.database import async_session as AsyncSessionLocal
            from app.services.news_llm_service import search_articles_by_keywords

            hours = settings.NEWS_CACHE_TTL // 3600

            async with AsyncSessionLocal() as db:
                db_results = await search_articles_by_keywords(
                    db, [""], hours=hours, limit=200
                )

            if not db_results:
                logger.info("No recent articles in DB for cache warming")
                return 0

            articles = self._map_db_results(db_results)
            await self._warm_cache_from_articles(articles)

            # 워밍 완료 플래그 설정
            await self._redis.set(_CACHE_WARMED_KEY, "1", ex=settings.NEWS_CACHE_TTL)

            logger.info(f"Cache warmed with {len(articles)} articles from DB")
            return len(articles)
        except Exception as e:
            logger.warning(f"Cache warming from DB failed: {e}")
            return 0

    # ─── DB 조회 ─────────────────────────────

    async def _load_from_db(
        self,
        category: str | None = None,
        query: str | None = None,
    ) -> list[NewsArticle]:
        """DB에서 최근 7시간 기사 조회"""
        try:
            from app.core.database import async_session as AsyncSessionLocal
            from app.services.news_llm_service import search_articles_by_keywords

            hours = settings.NEWS_CACHE_TTL // 3600
            keywords = [query] if query else [""]

            async with AsyncSessionLocal() as db:
                results = await search_articles_by_keywords(
                    db, keywords, hours=hours, limit=50
                )

            if not results:
                return []

            articles = self._map_db_results(results, category)
            return articles
        except Exception as e:
            logger.warning(f"DB load failed: {e}")
            return []

    async def _fetch_and_save(self, query: str, category: str) -> list[NewsArticle]:
        """API에서 뉴스 fetch → DB 저장 → 기사 반환"""
        raw = await self._fetch_news(query)
        if not raw:
            return []

        articles = self._map_raw_articles(raw, category)

        # DB 저장
        if articles:
            try:
                from app.core.database import async_session as AsyncSessionLocal
                from app.services.news_llm_service import save_articles_to_db

                async with AsyncSessionLocal() as db:
                    saved = await save_articles_to_db(db, articles)
                    logger.info(f"Saved {saved} articles to DB for query '{query}'")
            except Exception as e:
                logger.warning(f"Failed to save fetched articles to DB: {e}")

        return articles

    async def _save_raw_to_db(self, raw: list[dict], category: str) -> None:
        """원시 검색 결과를 DB에 저장"""
        articles = self._map_raw_articles(raw, category)
        if articles:
            try:
                from app.core.database import async_session as AsyncSessionLocal
                from app.services.news_llm_service import save_articles_to_db

                async with AsyncSessionLocal() as db:
                    await save_articles_to_db(db, articles)
            except Exception as e:
                logger.warning(f"Failed to save raw articles to DB: {e}")

    # ─── SearchProvider 연동 ─────────────────

    async def _fetch_news(self, query: str) -> list[dict]:
        """SearchProvider를 통해 뉴스 검색"""
        from app.services.search import get_search_provider

        provider = get_search_provider()
        return await provider.search_news(query)

    # ─── 매핑 / 유틸 ─────────────────────────

    def _map_raw_articles(
        self,
        raw: list[dict],
        category: str,
        related_asset: str | None = None,
    ) -> list[NewsArticle]:
        """원시 API 결과 → NewsArticle 변환"""
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
                        name=source_data.get("name", "") if isinstance(source_data, dict) else str(source_data),
                        icon=source_data.get("icon") if isinstance(source_data, dict) else None,
                    ),
                    snippet=(item.get("snippet") or item.get("content", ""))[:300],
                    thumbnail=item.get("thumbnail"),
                    published_at=item.get("date", ""),
                    category=category,
                    related_asset=related_asset,
                )
            )
        return articles

    def _map_db_results(
        self,
        db_results: list[dict],
        category: str | None = None,
    ) -> list[NewsArticle]:
        """DB 결과 → NewsArticle 변환"""
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
                    category=category or item.get("category", NewsCategory.ALL),
                    related_asset=item.get("related_asset"),
                )
            )
        return articles

    @staticmethod
    def _match_asset(item: dict, queries: list[str]) -> str | None:
        """기사 제목/snippet에서 매칭되는 자산명 찾기"""
        title_lower = (item.get("title") or "").lower()
        snippet_lower = (item.get("snippet") or item.get("content") or "").lower()
        for q in queries:
            if q.lower() in title_lower or q.lower() in snippet_lower:
                return q
        return None

    # ─── Redis 캐시 ──────────────────────────

    async def _warm_cache_from_articles(self, articles: list[NewsArticle]) -> None:
        """기사 목록을 카테고리별로 Redis에 캐시"""
        from collections import defaultdict

        by_category: dict[str, list[NewsArticle]] = defaultdict(list)
        for a in articles:
            by_category[a.category].append(a)
            by_category[NewsCategory.ALL].append(a)

        for cat, cat_articles in by_category.items():
            # 최신순 정렬
            sorted_articles = cat_articles[:50]  # 카테고리당 최대 50개
            result = NewsListResponse(
                articles=sorted_articles,
                page=1,
                per_page=len(sorted_articles),
                has_next=False,
            )
            cache_key = self._cache_key(cat)
            await self._set_cached(cache_key, result.model_dump())

    def _cache_key(self, category: str, query: str = "", page: int = 1) -> str:
        if query:
            query_hash = hashlib.md5(query.encode()).hexdigest()[:8]
            return f"{_CACHE_PREFIX}:{category}:{query_hash}:{page}"
        return f"{_CACHE_PREFIX}:{category}:{page}"

    async def _get_cached(self, key: str) -> dict | None:
        try:
            data = await self._redis.get(key)
            if data:
                return json.loads(data)
        except Exception:
            logger.warning(f"Redis cache read failed for {key}")
        return None

    async def _set_cached(self, key: str, data: dict) -> None:
        try:
            await self._redis.set(
                key, json.dumps(data, default=str, ensure_ascii=False), ex=settings.NEWS_CACHE_TTL
            )
        except Exception:
            logger.warning(f"Redis cache write failed for {key}")
