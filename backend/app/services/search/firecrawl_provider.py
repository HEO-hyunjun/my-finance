"""Firecrawl 검색 프로바이더 (셀프호스트 또는 클라우드)."""

import asyncio
import logging

from app.core.config import settings
from app.services.search.base import SearchProvider

logger = logging.getLogger(__name__)


class FirecrawlProvider(SearchProvider):

    def _get_client(self):
        from firecrawl import FirecrawlApp

        kwargs = {"api_key": settings.FIRECRAWL_API_KEY}
        if settings.FIRECRAWL_BASE_URL:
            kwargs["api_url"] = settings.FIRECRAWL_BASE_URL
        return FirecrawlApp(**kwargs)

    async def search_news(self, query: str, max_results: int = 20) -> list[dict]:
        if not settings.FIRECRAWL_API_KEY:
            logger.warning("FIRECRAWL_API_KEY not set, returning mock news")
            return self._mock_news(query)

        try:
            app = self._get_client()
            news_query = f"{query} 뉴스 최신"
            results = await asyncio.to_thread(
                app.search, news_query, {"limit": max_results}
            )

            raw_data = results.get("data", []) if isinstance(results, dict) else results

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

    async def web_search(self, query: str, max_results: int = 10) -> list[dict]:
        if not settings.FIRECRAWL_API_KEY:
            return []

        try:
            app = self._get_client()
            results = await asyncio.to_thread(
                app.search, query, {"limit": max_results}
            )

            raw_data = results.get("data", []) if isinstance(results, dict) else results

            return [
                {
                    "title": r.get("title", ""),
                    "link": r.get("url", ""),
                    "snippet": r.get("description", "") or (r.get("markdown", "") or "")[:200],
                }
                for r in raw_data
            ]
        except Exception as e:
            logger.warning(f"Firecrawl web search failed: {e}")
            return []
