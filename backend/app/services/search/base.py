"""검색 프로바이더 추상 인터페이스."""

from abc import ABC, abstractmethod


class SearchProvider(ABC):
    """뉴스/웹 검색 프로바이더 인터페이스.

    .env의 SEARCH_PROVIDER 값에 따라 구현체가 선택됩니다.
    - "tavily"   : Tavily (무료 월 1,000 크레딧)
    - "serpapi"   : SerpAPI (유료 구독)
    - "firecrawl" : Firecrawl (셀프호스트 또는 클라우드)
    """

    @abstractmethod
    async def search_news(
        self, query: str, max_results: int = 20, include_raw_content: bool = False,
    ) -> list[dict]:
        """뉴스 검색.

        Args:
            include_raw_content: True면 기사 전문 포함 (배치 LLM 처리용).
                                False면 snippet만 반환 (사용자 응답용).

        Returns:
            list[dict]: 각 항목은 아래 키를 포함:
                - title: str
                - link: str
                - source: dict (name, icon)
                - snippet: str | None
                - raw_content: str | None (include_raw_content=True일 때만)
                - thumbnail: str | None
                - date: str
        """

    @abstractmethod
    async def web_search(self, query: str, max_results: int = 10) -> list[dict]:
        """일반 웹 검색.

        Returns:
            list[dict]: 각 항목은 아래 키를 포함:
                - title: str
                - link: str
                - snippet: str
        """

    @staticmethod
    def _extract_domain(url: str) -> str:
        """URL에서 도메인명 추출."""
        try:
            from urllib.parse import urlparse
            parsed = urlparse(url)
            return parsed.netloc.replace("www.", "")
        except Exception:
            return ""

    @staticmethod
    def _mock_news(query: str) -> list[dict]:
        """API 키 미설정 시 더미 뉴스."""
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
