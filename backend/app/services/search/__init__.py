"""검색 프로바이더 팩토리.

.env의 SEARCH_PROVIDER 값에 따라 적절한 프로바이더 인스턴스를 반환합니다.

사용법:
    from app.services.search import get_search_provider

    provider = get_search_provider()
    results = await provider.search_news("코스피 코스닥")
    results = await provider.web_search("삼성전자 주가")
"""

import logging

from app.core.config import settings
from app.services.search.base import SearchProvider

logger = logging.getLogger(__name__)

_provider_instance: SearchProvider | None = None


def get_search_provider() -> SearchProvider:
    """SEARCH_PROVIDER 설정에 따라 싱글톤 프로바이더 반환."""
    global _provider_instance

    if _provider_instance is not None:
        return _provider_instance

    provider_name = settings.SEARCH_PROVIDER.lower()

    if provider_name == "serpapi":
        from app.services.search.serpapi_provider import SerpApiProvider
        _provider_instance = SerpApiProvider()
    elif provider_name == "firecrawl":
        from app.services.search.firecrawl_provider import FirecrawlProvider
        _provider_instance = FirecrawlProvider()
    else:  # tavily (default)
        from app.services.search.tavily_provider import TavilyProvider
        _provider_instance = TavilyProvider()

    logger.info(f"Search provider initialized: {provider_name}")
    return _provider_instance


__all__ = ["SearchProvider", "get_search_provider"]
