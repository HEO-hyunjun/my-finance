"""서브에이전트 기본 클래스.

각 서브에이전트는 특정 도메인의 도구를 가지고 ReAct 루프를 실행합니다.
오케스트레이터에 의해 호출됩니다.
"""

import json
import logging
import uuid
from abc import ABC, abstractmethod
from collections.abc import AsyncGenerator
from dataclasses import dataclass, field
from typing import Any

from litellm import acompletion
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.services.market_service import MarketService

logger = logging.getLogger(__name__)

# 도구 이름 → 사용자에게 보여줄 한글 레이블
TOOL_DISPLAY_NAMES: dict[str, str] = {
    # AssetAgent
    "get_asset_summary": "자산 포트폴리오 조회",
    "get_transactions": "거래 내역 조회",
    "get_market_price": "시세 조회",
    "get_exchange_rate": "환율 조회",
    "get_rebalancing_analysis": "리밸런싱 분석",
    # NewsAgent
    "query_news_db": "뉴스 DB 검색",
    "get_news_clusters": "뉴스 클러스터 조회",
    "search_news": "뉴스 검색",
    "web_search": "웹 검색",
    # BudgetAgent
    "get_budget_status": "예산 현황 조회",
    "get_budget_analysis": "예산 분석",
    "get_expense_list": "지출 내역 조회",
    "get_income_list": "수입 내역 조회",
    "get_fixed_expenses": "고정비 조회",
    "get_installments": "할부금 조회",
}


@dataclass
class SubAgentResult:
    """서브에이전트 실행 결과"""

    content: str
    tools_used: list[str] = field(default_factory=list)
    success: bool = True


class SubAgent(ABC):
    """서브에이전트 기본 클래스.

    각 서브에이전트는 자체 도구와 시스템 프롬프트를 가지며,
    ReAct 패턴으로 도구를 사용하여 질문에 답합니다.
    """

    name: str = "base"
    display_name: str = "기본"
    description: str = ""
    system_prompt: str = ""
    max_tool_rounds: int = 3

    @abstractmethod
    def get_tool_definitions(self) -> list[dict]:
        """도구 정의 반환"""

    @abstractmethod
    async def execute_tool(
        self,
        tool_name: str,
        args: dict,
        db: AsyncSession,
        user_id: uuid.UUID,
        market: MarketService,
    ) -> Any:
        """도구 실행"""

    async def run_stream(
        self,
        question: str,
        context: str,
        db: AsyncSession,
        user_id: uuid.UUID,
        market: MarketService,
    ) -> AsyncGenerator[dict[str, Any], None]:
        """서브에이전트 실행 (ReAct 루프) — 도구 호출 이벤트를 실시간으로 yield.

        Yields:
            {"type": "tool", "name": str, "display_name": str, "status": "calling"|"done"|"error"}
            {"type": "result", "content": str, "tools_used": list[str], "success": bool}
        """
        system_content = f"{self.system_prompt}\n\n## 사용자 재무 컨텍스트\n{context}"

        messages: list[dict] = [
            {"role": "system", "content": system_content},
            {"role": "user", "content": question},
        ]

        tools = self.get_tool_definitions()
        tools_used: list[str] = []
        tool_rounds = 0

        try:
            while tool_rounds < self.max_tool_rounds:
                kwargs: dict[str, Any] = {
                    "model": settings.chatbot_model,
                    "messages": messages,
                    "max_tokens": 1024,
                    "temperature": 0.3,
                }
                if tools:
                    kwargs["tools"] = tools
                    kwargs["tool_choice"] = "auto"

                response = await acompletion(**kwargs)
                message = response.choices[0].message

                if hasattr(message, "tool_calls") and message.tool_calls:
                    tool_rounds += 1
                    messages.append(message.model_dump())

                    for tc in message.tool_calls:
                        fn_name = tc.function.name
                        args = (
                            json.loads(tc.function.arguments)
                            if tc.function.arguments
                            else {}
                        )
                        tools_used.append(fn_name)
                        display = TOOL_DISPLAY_NAMES.get(fn_name, fn_name)

                        # 도구 호출 시작 이벤트
                        yield {
                            "type": "tool",
                            "name": fn_name,
                            "display_name": display,
                            "status": "calling",
                        }

                        try:
                            result = await self.execute_tool(
                                fn_name, args, db, user_id, market,
                            )
                            # 도구 호출 완료 이벤트
                            yield {
                                "type": "tool",
                                "name": fn_name,
                                "display_name": display,
                                "status": "done",
                            }
                        except Exception as e:
                            logger.warning(f"[{self.name}] Tool {fn_name} failed: {e}")
                            result = {"error": str(e)}
                            yield {
                                "type": "tool",
                                "name": fn_name,
                                "display_name": display,
                                "status": "error",
                            }

                        messages.append({
                            "role": "tool",
                            "tool_call_id": tc.id,
                            "content": json.dumps(
                                result, ensure_ascii=False, default=str,
                            ),
                        })

                    logger.info(
                        f"[{self.name}] Round {tool_rounds}: "
                        f"{[tc.function.name for tc in message.tool_calls]}"
                    )
                    continue

                # 도구 호출 없음 → 최종 응답
                yield {
                    "type": "result",
                    "content": message.content or "",
                    "tools_used": tools_used,
                    "success": True,
                }
                return

            # max rounds 도달 → 마지막 응답 생성
            final = await acompletion(
                model=settings.chatbot_model,
                messages=messages,
                max_tokens=1024,
                temperature=0.3,
            )
            yield {
                "type": "result",
                "content": final.choices[0].message.content or "",
                "tools_used": tools_used,
                "success": True,
            }

        except Exception as e:
            logger.error(f"[{self.name}] Error: {e}")
            yield {
                "type": "result",
                "content": f"분석 중 오류가 발생했습니다: {e}",
                "tools_used": tools_used,
                "success": False,
            }

    async def run(
        self,
        question: str,
        context: str,
        db: AsyncSession,
        user_id: uuid.UUID,
        market: MarketService,
    ) -> SubAgentResult:
        """서브에이전트 실행 (호환성용 래퍼) — run_stream을 소비하여 결과 반환"""
        async for event in self.run_stream(question, context, db, user_id, market):
            if event["type"] == "result":
                return SubAgentResult(
                    content=event["content"],
                    tools_used=event["tools_used"],
                    success=event["success"],
                )
        return SubAgentResult(content="", tools_used=[], success=False)
