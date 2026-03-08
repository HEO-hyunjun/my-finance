"""SerpAPI 검색 프로바이더 (유료 구독)."""

import logging

import httpx

from app.core.config import settings
from app.services.search.base import SearchProvider

logger = logging.getLogger(__name__)


class SerpApiProvider(SearchProvider):

    async def search_news(
        self, query: str, max_results: int = 20, include_raw_content: bool = False,
        category: str = "",
    ) -> list[dict]:
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

        try:
            async with httpx.AsyncClient(timeout=10.0) as client:
                resp = await client.get("https://serpapi.com/search", params=params)
                resp.raise_for_status()
                data = resp.json()

            return [
                {
                    "title": r.get("title", ""),
                    "link": r.get("link", ""),
                    "source": {
                        "name": r.get("source", {}).get("name", ""),
                        "icon": r.get("source", {}).get("icon"),
                    },
                    "snippet": r.get("snippet"),
                    "thumbnail": r.get("thumbnail"),
                    "date": r.get("date", ""),
                }
                for r in data.get("news_results", [])[:max_results]
                if r.get("title") and r.get("link")
            ]
        except Exception as e:
            logger.warning(f"SerpAPI news search failed: {e}")
            return self._mock_news(query)

    async def web_search(self, query: str, max_results: int = 10) -> list[dict]:
        if not settings.SERPAPI_KEY:
            return []

        params = {
            "engine": "google",
            "q": query,
            "num": max_results,
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
                for r in result.get("organic_results", [])[:max_results]
            ]
        except Exception as e:
            logger.warning(f"SerpAPI web search failed: {e}")
            return []
