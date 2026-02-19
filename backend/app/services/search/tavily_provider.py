"""Tavily 검색 프로바이더 (무료 월 1,000 크레딧).

NOTE: topic="general"을 사용해야 한국어 기사가 정상 반환됨.
      topic="news"는 영문 기사만 반환하는 Tavily 특성 때문에 사용하지 않음.
"""

import logging

from app.core.config import settings
from app.services.search.base import SearchProvider

logger = logging.getLogger(__name__)


class TavilyProvider(SearchProvider):

    async def search_news(self, query: str, max_results: int = 20) -> list[dict]:
        if not settings.TAVILY_API_KEY:
            logger.warning("TAVILY_API_KEY not set, returning mock news")
            return self._mock_news(query)

        try:
            from tavily import AsyncTavilyClient

            client = AsyncTavilyClient(api_key=settings.TAVILY_API_KEY)
            response = await client.search(
                query=query,
                topic="general",
                max_results=max_results,
                include_answer=False,
            )

            return [
                {
                    "title": r.get("title", ""),
                    "link": r.get("url", ""),
                    "source": {"name": self._extract_domain(r.get("url", "")), "icon": None},
                    "snippet": (r.get("content", "") or "")[:300],
                    "thumbnail": None,
                    "date": r.get("published_date", ""),
                }
                for r in response.get("results", [])
                if r.get("title") and r.get("url")
            ]
        except Exception as e:
            logger.warning(f"Tavily news search failed: {e}")
            return self._mock_news(query)

    async def web_search(self, query: str, max_results: int = 10) -> list[dict]:
        if not settings.TAVILY_API_KEY:
            return []

        try:
            from tavily import AsyncTavilyClient

            client = AsyncTavilyClient(api_key=settings.TAVILY_API_KEY)
            response = await client.search(
                query=query,
                topic="general",
                max_results=max_results,
                include_answer=False,
            )

            return [
                {
                    "title": r.get("title", ""),
                    "link": r.get("url", ""),
                    "snippet": (r.get("content", "") or "")[:300],
                }
                for r in response.get("results", [])
            ]
        except Exception as e:
            logger.warning(f"Tavily web search failed: {e}")
            return []
