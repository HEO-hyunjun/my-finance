import json
import logging

from app.services.agents.base import BaseAgent

logger = logging.getLogger(__name__)


class ResearcherAgent(BaseAgent):
    name = "researcher"
    description = "시세, 뉴스, 시장 데이터 검색 및 정리"
    system_prompt = """당신은 금융 리서치 전문가입니다.

## 역할
- 시세 데이터, 환율, 금 가격 등 시장 정보를 정리합니다.
- 최신 금융 뉴스와 트렌드를 분석합니다.
- 데이터를 표와 수치로 명확하게 정리합니다.

## 2-Layer 검색 전략 (필수!)
정보 검색 시 반드시 다음 순서를 따릅니다:
1. **Layer 1 (DB 우선 - 항상 먼저!)**: query_news_db를 항상 먼저 호출합니다. DB에는 하루 2회 수집된 최신 뉴스가 LLM 요약과 함께 저장되어 있어 품질이 높습니다.
2. **Layer 2 (실시간 API - DB에 정보 부족 시만!)**: DB에 충분한 정보가 없을 경우에만 search_news, web_search를 사용합니다. API 호출 쿼터가 매우 제한적(월 100건)이므로 꼭 필요한 경우에만 사용하세요.

## 도구 사용
- DB에 저장된 분석 뉴스 조회: query_news_db (Layer 1 - **항상 먼저 호출!**)
- 실시간 시세: get_market_price (yfinance 기반, 쿼터 무관)
- 실시간 뉴스 검색: search_news (Layer 2 - **쿼터 제한! DB에 없을 때만 사용**)
- 웹 검색: web_search (Layer 2 - **쿼터 제한! DB에 없을 때만 사용**)
- 환율 정보: get_exchange_rate (yfinance 기반, 쿼터 무관)

## 응답 규칙
- 마크다운 테이블을 활용하여 데이터를 정리합니다.
- 금액은 원화(₩) 기준, 천 단위 구분자 사용
- 출처와 시점을 명시합니다.
- 객관적 데이터 중심, 주관적 의견은 최소화합니다."""

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
                "name": "search_news",
                "description": "금융 관련 최신 뉴스를 실시간 검색합니다 (⚠️ 쿼터 제한: 월 100건! DB에 정보가 없을 때만 사용)",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "query": {
                            "type": "string",
                            "description": "검색 키워드 (예: 삼성전자, 미국 금리, 비트코인)",
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
        {
            "type": "function",
            "function": {
                "name": "query_news_db",
                "description": "DB에 저장된 LLM 분석 완료 뉴스를 검색합니다 (Layer 1 - 빠름, 요약/감성 포함)",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "category": {
                            "type": "string",
                            "description": "뉴스 카테고리 (all, stock_kr, stock_us, gold, economy)",
                        },
                    },
                },
            },
        },
        {
            "type": "function",
            "function": {
                "name": "web_search",
                "description": "웹에서 실시간 정보를 검색합니다 (⚠️ 쿼터 제한: 월 100건! query_news_db에 정보가 없을 때만 사용)",
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
    ]

    KEYWORDS = [
        "시세", "가격", "환율", "뉴스", "시장", "현재", "얼마",
        "price", "rate", "market", "trend", "종목", "주가",
    ]

    def can_handle(self, query: str) -> float:
        query_lower = query.lower()
        matches = sum(1 for kw in self.KEYWORDS if kw in query_lower)
        return min(matches * 0.25, 1.0)

    async def _execute_tools(
        self, tool_calls: list, tools_context: dict
    ) -> list[dict]:
        """2-Layer tool 실행: DB캐시(Layer1) + Tavily(Layer2)"""
        from app.services.market_service import MarketService
        from app.services.news_service import NewsService

        market: MarketService | None = tools_context.get("market")
        news: NewsService | None = tools_context.get("news")
        db = tools_context.get("db")
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

                elif fn_name == "search_news" and news:
                    news_response = await news.search_news(
                        query=args["query"], per_page=5
                    )
                    result_data = [
                        {
                            "title": a.title,
                            "source": a.source.name,
                            "snippet": a.snippet,
                            "link": a.link,
                            "published_at": a.published_at,
                        }
                        for a in news_response.articles
                    ]

                elif fn_name == "get_exchange_rate" and market:
                    rate_data = await market.get_exchange_rate()
                    result_data = {
                        "pair": rate_data.pair,
                        "rate": rate_data.rate,
                        "change": rate_data.change,
                        "change_percent": rate_data.change_percent,
                    }

                elif fn_name == "query_news_db" and db:
                    from app.services.news_llm_service import get_processed_articles
                    category = args.get("category", "all")
                    articles = await get_processed_articles(db, category, limit=10)
                    result_data = articles if articles else {"message": "분석된 뉴스가 없습니다"}

                elif fn_name == "web_search" and market:
                    search_results = await market.web_search(args["query"])
                    result_data = search_results if search_results else {"message": "검색 결과가 없습니다"}

                else:
                    result_data = {"error": f"Unknown tool or service unavailable: {fn_name}"}

            except Exception as e:
                logger.warning(f"Tool {fn_name} execution failed: {e}")
                result_data = {"error": str(e)}

            results.append({
                "role": "tool",
                "tool_call_id": tc.id,
                "content": json.dumps(result_data, ensure_ascii=False, default=str),
            })

        return results
