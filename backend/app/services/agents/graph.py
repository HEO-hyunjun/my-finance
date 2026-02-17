"""ReAct 기반 에이전트 그래프.

단일 에이전트가 모든 도구를 보유하고, LLM이 직접 판단하여
필요한 도구를 호출(Act) → 결과 관찰(Observe) → 다시 판단을 반복합니다.
최종 응답은 스트리밍으로 전달됩니다.
"""

import json
import logging
import uuid
from collections.abc import AsyncGenerator
from typing import Any

from litellm import acompletion
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.core.redis import get_redis
from app.services.agents.checkpoint import RedisCheckpointStore
from app.services.market_service import MarketService
from app.services.news_service import NewsService

logger = logging.getLogger(__name__)

MAX_TOOL_ROUNDS = 5  # 무한 루프 방지

# ── 통합 시스템 프롬프트 ──

SYSTEM_PROMPT = """당신은 개인 재무 AI 어시스턴트입니다.

## 역할
- 포트폴리오 분석, 예산 관리, 투자 전략 상담을 제공합니다.
- 필요하면 실시간 시세, 뉴스, 환율 데이터를 직접 조회합니다.
- 사용자의 재무 현황을 기반으로 구체적인 조언을 합니다.

## 도구 사용 전략
- 시세/가격 질문 → get_market_price (무제한)
- 환율 질문 → get_exchange_rate (무제한)
- 뉴스 질문 → query_news_db를 **항상 먼저** 호출! DB에 없을 때만 search_news
- 정보 검색 → query_news_db 먼저 → 없으면 web_search
- 예산/지출 현황 → get_budget_status (카테고리별 예산 사용률 포함)
- 지출 내역 조회 → get_expense_list (날짜/카테고리 필터 가능)
- 수입 내역 조회 → get_income_list (날짜/유형 필터 가능)
- ⚠️ search_news, web_search는 월 100건 쿼터 제한! 꼭 필요할 때만 사용
- 도구가 필요 없는 질문(일반 상담 등)은 도구 없이 바로 답변

## 응답 규칙
- 금액은 ₩ 기호와 천 단위 구분자 사용
- 데이터 시점을 명시 (예: "2026-02-15 기준")
- 투자 관련 답변 시 리스크 언급
- 마크다운 테이블, 리스트 등으로 가독성 높게 정리
- 한국어로 답변"""


# ── 통합 도구 정의 (중복 제거) ──

TOOL_DEFINITIONS = [
    {
        "type": "function",
        "function": {
            "name": "get_market_price",
            "description": "종목의 실시간 시세를 조회합니다 (yfinance 기반, 쿼터 무관)",
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
            "name": "get_exchange_rate",
            "description": "USD/KRW 환율 정보를 조회합니다 (yfinance 기반, 쿼터 무관)",
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
            "description": "DB에 저장된 LLM 분석 완료 뉴스를 검색합니다 (빠름, 요약/감성 포함, 항상 먼저 사용!)",
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
            "description": "금융 관련 최신 뉴스를 실시간 검색합니다 (⚠️ 월 100건 쿼터! query_news_db에 없을 때만 사용)",
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
            "description": "웹에서 실시간 정보를 검색합니다 (⚠️ 월 100건 쿼터! query_news_db에 없을 때만 사용)",
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
            "name": "get_budget_status",
            "description": "사용자의 이번 달 예산 현황을 조회합니다 (총 예산, 지출, 잔여액, 카테고리별 사용률 포함)",
            "parameters": {
                "type": "object",
                "properties": {},
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "get_expense_list",
            "description": "사용자의 지출 내역을 조회합니다 (최근 지출, 날짜/카테고리 필터 가능)",
            "parameters": {
                "type": "object",
                "properties": {
                    "start_date": {
                        "type": "string",
                        "description": "조회 시작일 (YYYY-MM-DD, 미지정 시 이번 달)",
                    },
                    "end_date": {
                        "type": "string",
                        "description": "조회 종료일 (YYYY-MM-DD, 미지정 시 오늘)",
                    },
                },
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "get_income_list",
            "description": "사용자의 수입 내역을 조회합니다 (급여, 부수입, 투자수익 등)",
            "parameters": {
                "type": "object",
                "properties": {
                    "start_date": {
                        "type": "string",
                        "description": "조회 시작일 (YYYY-MM-DD, 미지정 시 이번 달)",
                    },
                    "end_date": {
                        "type": "string",
                        "description": "조회 종료일 (YYYY-MM-DD, 미지정 시 오늘)",
                    },
                    "income_type": {
                        "type": "string",
                        "description": "수입 유형 필터 (salary, side, investment, other)",
                    },
                },
            },
        },
    },
]


# ── 도구 실행 ──


async def execute_tools(
    tool_calls: list,
    market: MarketService,
    db: AsyncSession,
    user_id: uuid.UUID | None = None,
) -> list[dict]:
    """도구 호출을 실행하고 결과를 반환"""
    redis_client = await get_redis()
    news = NewsService(redis_client)
    results = []

    for tc in tool_calls:
        fn_name = tc.function.name
        args = json.loads(tc.function.arguments) if tc.function.arguments else {}
        result_data: dict | list = {"error": f"Unknown tool: {fn_name}"}

        try:
            if fn_name == "get_market_price":
                price_data = await market.get_price(args["symbol"], asset_type=None)
                result_data = {
                    "symbol": price_data.symbol,
                    "name": price_data.name,
                    "price": price_data.price,
                    "currency": price_data.currency,
                    "change": price_data.change,
                    "change_percent": price_data.change_percent,
                }

            elif fn_name == "get_exchange_rate":
                rate_data = await market.get_exchange_rate()
                result_data = {
                    "pair": rate_data.pair,
                    "rate": rate_data.rate,
                    "change": rate_data.change,
                    "change_percent": rate_data.change_percent,
                }

            elif fn_name == "query_news_db":
                from app.services.news_llm_service import get_processed_articles

                category = args.get("category", "all")
                articles = await get_processed_articles(db, category, limit=10)
                result_data = articles or {"message": "분석된 뉴스가 없습니다"}

            elif fn_name == "search_news":
                news_response = await news.search_news(query=args["query"], per_page=5)
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

            elif fn_name == "web_search":
                search_results = await market.web_search(args["query"])
                result_data = search_results or {"message": "검색 결과가 없습니다"}

            elif fn_name == "get_budget_status" and user_id:
                from app.services.budget_service import get_budget_summary
                from sqlalchemy import select as sa_select
                from app.models.user import User as UserModel

                stmt = sa_select(UserModel.salary_day).where(UserModel.id == user_id)
                row = await db.execute(stmt)
                salary_day = row.scalar_one_or_none() or 1

                summary = await get_budget_summary(
                    db, user_id, salary_day=salary_day,
                )
                result_data = json.loads(summary.model_dump_json())

            elif fn_name == "get_expense_list" and user_id:
                from datetime import date as date_type
                from app.services.budget_service import get_expenses

                start = date_type.fromisoformat(args["start_date"]) if args.get("start_date") else None
                end = date_type.fromisoformat(args["end_date"]) if args.get("end_date") else None

                expense_resp = await get_expenses(
                    db, user_id,
                    start_date=start,
                    end_date=end,
                    per_page=15,
                )
                result_data = json.loads(expense_resp.model_dump_json())

            elif fn_name == "get_income_list" and user_id:
                from datetime import date as date_type
                from app.services.income_service import get_incomes

                start = date_type.fromisoformat(args["start_date"]) if args.get("start_date") else None
                end = date_type.fromisoformat(args["end_date"]) if args.get("end_date") else None
                income_type = args.get("income_type")

                income_resp = await get_incomes(
                    db, user_id,
                    income_type=income_type,
                    start_date=start,
                    end_date=end,
                    per_page=15,
                )
                result_data = json.loads(income_resp.model_dump_json())

        except Exception as e:
            logger.warning(f"Tool {fn_name} failed: {e}")
            result_data = {"error": str(e)}

        results.append({
            "role": "tool",
            "tool_call_id": tc.id,
            "content": json.dumps(result_data, ensure_ascii=False, default=str),
        })

    return results


# ── AgentGraph ──


class AgentGraph:
    """ReAct 에이전트 그래프.

    reason → act (tool call) → observe → reason → ... → stream response
    체크포인트는 Redis에 대화별로 저장됩니다.
    """

    def __init__(self):
        self._checkpoint_store: RedisCheckpointStore | None = None

    async def _get_checkpoint_store(self) -> RedisCheckpointStore:
        if self._checkpoint_store is None:
            redis = await get_redis()
            self._checkpoint_store = RedisCheckpointStore(redis)
        return self._checkpoint_store

    async def run_stream(
        self,
        *,
        db: AsyncSession,
        user_id: uuid.UUID,
        query: str,
        conversation_id: str,
        history: list[dict[str, str]],
        market: MarketService,
    ) -> AsyncGenerator[dict[str, Any], None]:
        """ReAct 루프 실행 (스트리밍).

        Yields:
            {"type": "tool", "name": str, "args": dict}  — 도구 호출 시작
            {"type": "token", "content": str}             — 스트리밍 토큰
            {"type": "done", "state": dict}               — 완료
            {"type": "error", "message": str}             — 에러
        """

        # ── 1. 컨텍스트 구성 ──
        from app.services.chatbot_service import build_financial_context, load_user_patterns

        financial_context = await build_financial_context(db, user_id, market)

        user_patterns = await load_user_patterns(db, user_id)
        if user_patterns:
            financial_context += "\n\n" + user_patterns

        # 투자 철학 로드
        from sqlalchemy import select
        from app.models.user import User

        stmt = select(User.investment_prompt).where(User.id == user_id)
        result = await db.execute(stmt)
        investment_prompt = result.scalar_one_or_none()

        system_prompt = f"{SYSTEM_PROMPT}\n\n## 사용자 재무 현황\n{financial_context}"
        if investment_prompt:
            system_prompt += f"\n\n## 사용자 투자 철학/전략\n{investment_prompt}"

        # ── 2. LLM 메시지 구성 ──
        llm_messages: list[dict] = [
            {"role": "system", "content": system_prompt},
            *history,
            {"role": "user", "content": query},
        ]

        # ── 3. ReAct 루프 (도구 호출 반복) ──
        tool_rounds = 0

        try:
            while tool_rounds < MAX_TOOL_ROUNDS:
                response = await acompletion(
                    model=settings.chatbot_model,
                    messages=llm_messages,
                    max_tokens=settings.CHATBOT_MAX_TOKENS,
                    temperature=settings.CHATBOT_TEMPERATURE,
                    tools=TOOL_DEFINITIONS,
                    tool_choice="auto",
                )

                message = response.choices[0].message

                # 도구 호출이 있으면 → 실행 → 결과 추가 → 다음 라운드
                if hasattr(message, "tool_calls") and message.tool_calls:
                    tool_rounds += 1

                    # 프론트엔드에 도구 사용 알림
                    for tc in message.tool_calls:
                        args = json.loads(tc.function.arguments) if tc.function.arguments else {}
                        yield {"type": "tool", "name": tc.function.name, "args": args}

                    # 도구 실행
                    tool_results = await execute_tools(message.tool_calls, market, db, user_id)

                    # LLM 메시지에 추가
                    llm_messages.append(message.model_dump())
                    llm_messages.extend(tool_results)

                    logger.info(
                        f"[ReAct] Round {tool_rounds}: "
                        f"{[tc.function.name for tc in message.tool_calls]}"
                    )
                    continue

                # 도구 호출 없음 → 텍스트 응답이 있으면 바로 전송
                if message.content:
                    # non-streaming 응답을 토큰처럼 전달
                    yield {"type": "token", "content": message.content}
                break

        except Exception as e:
            logger.error(f"[ReAct] Error: {e}")
            yield {"type": "error", "message": "AI 응답 생성 중 오류가 발생했습니다."}
            return

        # ── 4. 최종 응답 스트리밍 ──
        # 도구 사용 후 최종 응답은 스트리밍으로 생성
        if tool_rounds > 0:
            full_response = ""
            try:
                stream_response = await acompletion(
                    model=settings.chatbot_model,
                    messages=llm_messages,
                    max_tokens=settings.CHATBOT_MAX_TOKENS,
                    temperature=settings.CHATBOT_TEMPERATURE,
                    stream=True,
                )

                async for chunk in stream_response:
                    delta = chunk.choices[0].delta
                    if delta.content:
                        full_response += delta.content
                        yield {"type": "token", "content": delta.content}

            except Exception as e:
                logger.error(f"[ReAct] Stream error: {e}")
                yield {"type": "error", "message": "AI 응답 생성 중 오류가 발생했습니다."}
                return

        # ── 5. 체크포인트 저장 ──
        store = await self._get_checkpoint_store()
        prev_state = await store.load(conversation_id)

        checkpoint_data = {
            "message_count": ((prev_state or {}).get("message_count", 0)) + 2,
            "tool_rounds": tool_rounds,
            "last_query": query[:100],
        }
        await store.save(conversation_id, checkpoint_data)

        yield {"type": "done", "state": checkpoint_data}

    def get_agent_info(self) -> list[dict]:
        """사용 가능한 도구 정보 반환"""
        return [
            {
                "name": t["function"]["name"],
                "description": t["function"]["description"],
            }
            for t in TOOL_DEFINITIONS
        ]
