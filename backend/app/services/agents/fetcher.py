import json
import logging

from app.services.agents.base import BaseAgent

logger = logging.getLogger(__name__)


class FetcherAgent(BaseAgent):
    """실시간 데이터 검색/수집 전문 에이전트.

    Tavily를 통해 시세, 뉴스, 웹 검색 결과를 가져오고
    사용자 질문에 맞는 최신 데이터를 제공합니다.
    ResearcherAgent와 달리 분석 없이 데이터 수집에 집중합니다.
    """

    name = "fetcher"
    description = "실시간 시세, 웹 검색 데이터 수집"
    system_prompt = """당신은 실시간 금융 데이터 수집 전문가입니다.

## 역할
- 사용자가 요청한 시세, 정보를 실시간으로 검색합니다.
- 검색 결과를 깔끔하게 정리하여 제공합니다.
- 정보의 출처와 시점을 명확히 표시합니다.

## 도구 사용 전략
1. 시세 관련 질문 → get_market_price (yfinance, 쿼터 무관)
2. 일반 정보 질문 → web_search
3. 환율 질문 → get_exchange_rate (yfinance, 쿼터 무관)
4. 복합 질문 → 여러 도구 조합

## 응답 규칙
- 검색 결과를 마크다운 테이블로 정리합니다.
- 금액은 ₩ 기호와 천 단위 구분자를 사용합니다.
- 데이터 시점을 명시합니다 (예: "2026-02-15 기준").
- 검색 결과가 없으면 솔직하게 알립니다."""

    tool_definitions = [
        {
            "type": "function",
            "function": {
                "name": "get_market_price",
                "description": "종목의 실시간 시세를 조회합니다",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "symbol": {
                            "type": "string",
                            "description": "종목 심볼 (예: AAPL, 005930.KS, GLD)",
                        },
                    },
                    "required": ["symbol"],
                },
            },
        },
        {
            "type": "function",
            "function": {
                "name": "web_search",
                "description": "웹에서 실시간 정보를 검색합니다",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "query": {
                            "type": "string",
                            "description": "검색 키워드",
                        },
                    },
                    "required": ["query"],
                },
            },
        },
        {
            "type": "function",
            "function": {
                "name": "get_exchange_rate",
                "description": "USD/KRW 환율 정보를 조회합니다",
                "parameters": {
                    "type": "object",
                    "properties": {},
                },
            },
        },
    ]

    KEYWORDS = [
        "검색", "찾아", "조회", "알려", "보여", "최신",
        "지금", "오늘", "현재", "실시간", "search", "find",
        "look up", "fetch", "show", "what is",
    ]

    def can_handle(self, query: str) -> float:
        query_lower = query.lower()
        matches = sum(1 for kw in self.KEYWORDS if kw in query_lower)
        return min(matches * 0.2, 0.8)

    async def _execute_tools(
        self, tool_calls: list, tools_context: dict
    ) -> list[dict]:
        """Tool 실행: yfinance + 웹 검색 기반 실시간 데이터 수집"""
        from app.services.market_service import MarketService

        market: MarketService | None = tools_context.get("market")
        results = []

        for tc in tool_calls:
            fn_name = tc.function.name
            args = json.loads(tc.function.arguments) if tc.function.arguments else {}
            result_data: dict | list = {"error": "Tool not available"}

            try:
                if fn_name == "get_market_price" and market:
                    price_data = await market.get_price(
                        args["symbol"], asset_type=None
                    )
                    result_data = {
                        "symbol": price_data.symbol,
                        "name": price_data.name,
                        "price": price_data.price,
                        "currency": price_data.currency,
                        "change": price_data.change,
                        "change_percent": price_data.change_percent,
                    }

                elif fn_name == "web_search":
                    from app.services.search import get_search_provider
                    provider = get_search_provider()
                    search_results = await provider.web_search(args["query"])
                    result_data = search_results or {"message": "검색 결과가 없습니다"}

                elif fn_name == "get_exchange_rate" and market:
                    rate_data = await market.get_exchange_rate()
                    result_data = {
                        "pair": rate_data.pair,
                        "rate": rate_data.rate,
                        "change": rate_data.change,
                        "change_percent": rate_data.change_percent,
                    }

                else:
                    result_data = {"error": f"Unknown tool: {fn_name}"}

            except Exception as e:
                logger.warning(f"Fetcher tool {fn_name} failed: {e}")
                result_data = {"error": str(e)}

            results.append({
                "role": "tool",
                "tool_call_id": tc.id,
                "content": json.dumps(result_data, ensure_ascii=False, default=str),
            })

        return results
