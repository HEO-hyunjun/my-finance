"""뉴스 분석 서브에이전트.

DB의 뉴스를 검색하고, 클러스터를 분석하며, 필요시 실시간 검색합니다.
"""

import json
import uuid
from typing import Any

from sqlalchemy.ext.asyncio import AsyncSession

from app.services.agents.sub_agent import SubAgent
from app.services.market_service import MarketService


class NewsAgent(SubAgent):
    name = "news"
    display_name = "뉴스 분석"
    description = "뉴스 검색, 시장 동향, 경제 이슈 분석"
    system_prompt = """당신은 금융 뉴스 분석 전문가입니다.

## 역할
- DB에 저장된 LLM 분석 뉴스를 검색하고 종합합니다.
- 뉴스 클러스터(주제별 그룹)를 분석하여 시장 동향을 파악합니다.
- 필요시 실시간 뉴스와 웹 정보를 검색합니다.

## 도구 사용 전략
- query_news_db를 **항상 먼저** 호출! (빠르고, 요약/감성 분석 포함)
- get_news_clusters로 주요 뉴스 흐름 파악
- DB에 충분한 정보가 없을 때만 search_news 사용 (월 100건 쿼터!)
- web_search는 최후의 수단 (월 100건 쿼터!)

## 분석 방법
- 감성 점수(-1~1)를 기반으로 시장 분위기 판단
- 키워드 빈도로 주요 이슈 파악
- 뉴스 클러스터의 중요도 점수로 핵심 뉴스 선별

## 응답 규칙
- 뉴스 출처와 발행일을 명시
- 감성 분석 결과를 긍정/부정/중립으로 표시
- 핵심 뉴스를 요약하여 테이블로 정리"""

    def get_tool_definitions(self) -> list[dict]:
        return [
            {
                "type": "function",
                "function": {
                    "name": "query_news_db",
                    "description": "DB에 저장된 LLM 분석 뉴스 검색 (요약/감성 분석 포함, 항상 먼저 사용!)",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "category": {
                                "type": "string",
                                "description": "뉴스 카테고리 (all, stock_kr, stock_us, gold, economy)",
                            },
                            "keywords": {
                                "type": "string",
                                "description": "검색 키워드 (선택, 쉼표 구분)",
                            },
                        },
                    },
                },
            },
            {
                "type": "function",
                "function": {
                    "name": "get_news_clusters",
                    "description": "뉴스 클러스터(주제별 그룹) 조회 (요약, 감성, 중요도 포함)",
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
                    "name": "search_news",
                    "description": "금융 최신 뉴스 실시간 검색 (월 100건 쿼터! DB에 없을 때만 사용)",
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
                    "name": "web_search",
                    "description": "웹 실시간 정보 검색 (월 100건 쿼터! 다른 도구로 부족할 때만 사용)",
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
                    "name": "get_market_price",
                    "description": "종목 실시간 시세 조회 (뉴스와 연계 분석용)",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "symbol": {
                                "type": "string",
                                "description": "종목 심볼 (예: AAPL, 005930.KS)",
                            },
                        },
                        "required": ["symbol"],
                    },
                },
            },
        ]

    async def execute_tool(
        self,
        tool_name: str,
        args: dict,
        db: AsyncSession,
        user_id: uuid.UUID,
        market: MarketService,
    ) -> Any:
        if tool_name == "query_news_db":
            from app.services.news_llm_service import (
                get_processed_articles,
                search_articles_by_keywords,
            )

            keywords = args.get("keywords")
            if keywords:
                articles = await search_articles_by_keywords(
                    db, [k.strip() for k in keywords.split(",")], limit=10,
                )
            else:
                category = args.get("category", "all")
                articles = await get_processed_articles(db, category, limit=10)

            return articles or {"message": "분석된 뉴스가 없습니다"}

        if tool_name == "get_news_clusters":
            from app.services.news_llm_service import get_clusters

            category = args.get("category")
            clusters = await get_clusters(db, category=category, limit=10)
            return clusters or {"message": "뉴스 클러스터가 없습니다"}

        if tool_name == "search_news":
            from app.core.redis import get_redis
            from app.services.news_service import NewsService

            redis = await get_redis()
            news = NewsService(redis)
            news_response = await news.search_news(query=args["query"], per_page=5)
            return [
                {
                    "title": a.title,
                    "source": a.source.name,
                    "snippet": a.snippet,
                    "link": a.link,
                    "published_at": a.published_at,
                }
                for a in news_response.articles
            ]

        if tool_name == "web_search":
            search_results = await market.web_search(args["query"])
            return search_results or {"message": "검색 결과가 없습니다"}

        if tool_name == "get_market_price":
            price_data = await market.get_price(args["symbol"], asset_type=None)
            return {
                "symbol": price_data.symbol,
                "name": price_data.name,
                "price": price_data.price,
                "currency": price_data.currency,
                "change": price_data.change,
                "change_percent": price_data.change_percent,
            }

        return {"error": f"Unknown tool: {tool_name}"}
