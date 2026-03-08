"""Tavily 검색 프로바이더 (무료 월 1,000 크레딧).

한국어 카테고리: topic="general" + include_domains (한국 언론사)
영문 카테고리(stock_us): topic="news" + include_domains (해외 금융매체)
"""

import logging

from app.core.config import settings
from app.services.search.base import SearchProvider

logger = logging.getLogger(__name__)

# 한국 주요 금융/경제 뉴스 도메인
_KR_NEWS_DOMAINS = [
    # 경제 전문지
    "hankyung.com", "mk.co.kr", "sedaily.com", "mt.co.kr",
    "edaily.co.kr", "etoday.co.kr", "fnnews.com", "asiae.co.kr",
    # 종합 언론
    "yna.co.kr", "yonhapnewstv.co.kr", "newsis.com",
    "chosun.com", "donga.com", "joongang.co.kr",
    "hani.co.kr", "khan.co.kr", "kmib.co.kr",
    # 방송
    "sbs.co.kr", "kbs.co.kr", "mbc.co.kr", "jtbc.co.kr",
    # 증권/금융 전문
    "news.einfomax.co.kr", "thebell.co.kr", "bloter.net",
    "zdnet.co.kr", "etnews.com",
]

# 해외 금융 뉴스 도메인
_GLOBAL_NEWS_DOMAINS = [
    "bloomberg.com", "reuters.com", "cnbc.com",
    "investing.com", "marketwatch.com", "finance.yahoo.com",
    "wsj.com", "ft.com",
]

# 뉴스 부적합 도메인
_EXCLUDE_DOMAINS = [
    "tiktok.com", "instagram.com", "facebook.com",
    "blog.naver.com", "m.blog.naver.com", "tistory.com",
    "youtube.com", "brunch.co.kr", "medium.com",
    "pinterest.com", "reddit.com",
]

# 영문 카테고리 판별용
_GLOBAL_CATEGORIES = {"stock_us"}


class TavilyProvider(SearchProvider):

    async def search_news(
        self, query: str, max_results: int = 20, include_raw_content: bool = False,
        category: str = "",
    ) -> list[dict]:
        if not settings.TAVILY_API_KEY:
            logger.warning("TAVILY_API_KEY not set, returning mock news")
            return self._mock_news(query)

        try:
            from tavily import AsyncTavilyClient
            client = AsyncTavilyClient(api_key=settings.TAVILY_API_KEY)

            if category in _GLOBAL_CATEGORIES:
                # 해외 카테고리: topic="news" (영문 기사 품질 우수)
                return await self._search_global(client, query, max_results, include_raw_content)
            else:
                # 한국어 카테고리: topic="general" + 한국 언론사 도메인
                return await self._search_korean(client, query, max_results, include_raw_content)
        except Exception as e:
            logger.warning(f"Tavily news search failed: {e}")
            return self._mock_news(query)

    async def _search_korean(
        self, client, query: str, max_results: int, include_raw_content: bool,
    ) -> list[dict]:
        """한국어 뉴스 검색: topic=general + 한국 언론사 도메인 필터."""
        response = await client.search(
            query=query,
            topic="general",
            max_results=max_results,
            include_domains=_KR_NEWS_DOMAINS,
            include_answer=False,
            include_images=True,
            include_favicon=True,
            include_raw_content=include_raw_content,
        )
        results = self._parse_results(response, include_raw_content)

        # 결과 부족 시 도메인 제한 풀고 exclude로 필터
        if len(results) < 5:
            logger.info(f"Korean domain search returned {len(results)}, broadening search")
            fallback = await client.search(
                query=query,
                topic="general",
                max_results=max_results,
                exclude_domains=_EXCLUDE_DOMAINS,
                include_answer=False,
                include_images=True,
                include_favicon=True,
                include_raw_content=include_raw_content,
            )
            seen = {r["link"] for r in results}
            for item in self._parse_results(fallback, include_raw_content):
                if item["link"] not in seen:
                    results.append(item)
                    seen.add(item["link"])

        return results

    async def _search_global(
        self, client, query: str, max_results: int, include_raw_content: bool,
    ) -> list[dict]:
        """해외 뉴스 검색: topic=news + 글로벌 금융매체 도메인."""
        response = await client.search(
            query=query,
            topic="news",
            days=3,
            max_results=max_results,
            include_domains=_GLOBAL_NEWS_DOMAINS,
            include_answer=False,
            include_images=True,
            include_favicon=True,
            include_raw_content=include_raw_content,
        )
        return self._parse_results(response, include_raw_content)

    def _parse_results(self, response: dict, include_raw_content: bool) -> list[dict]:
        """Tavily 응답을 표준 포맷으로 변환."""
        return [
            {
                "title": r.get("title", ""),
                "link": r.get("url", ""),
                "source": {"name": self._extract_domain(r.get("url", "")), "icon": r.get("favicon")},
                "snippet": (r.get("content", "") or "")[:300],
                **({"raw_content": r.get("raw_content") or r.get("content") or ""} if include_raw_content else {}),
                "thumbnail": (r.get("images") or [None])[0] if r.get("images") else None,
                "date": r.get("published_date", ""),
            }
            for r in response.get("results", [])
            if r.get("title") and r.get("url")
        ]

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
