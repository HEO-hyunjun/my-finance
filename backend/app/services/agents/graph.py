"""오케스트레이터 기반 에이전트 그래프.

오케스트레이터가 사용자 질문을 분석하여 적절한 서브에이전트에게 위임하고,
결과를 종합하여 최종 응답을 스트리밍으로 생성합니다.
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
from app.services.agents.asset_agent import AssetAgent
from app.services.agents.budget_agent import BudgetAgent
from app.services.agents.checkpoint import RedisCheckpointStore
from app.services.agents.sub_agent import SubAgent
from app.services.market_service import MarketService

logger = logging.getLogger(__name__)

MAX_ORCHESTRATOR_ROUNDS = 3

# ── 오케스트레이터 시스템 프롬프트 ──

ORCHESTRATOR_PROMPT = """당신은 MyFinance 앱의 AI 재무 상담 오케스트레이터입니다.

## 역할
사용자의 질문을 분석하여 적절한 전문 에이전트에게 위임하고, 결과를 종합하여 답변합니다.

## 전문 에이전트
1. **자산 분석 에이전트** (ask_asset_agent): 포트폴리오, 보유 자산, 거래 내역, 시세, 수익률, 리밸런싱
2. **가계부 분석 에이전트** (ask_budget_agent): 예산, 지출, 수입, 고정비, 할부금, 가계 분석

## 위임 전략
- 질문 내용에 맞는 에이전트에 위임합니다.
- 복합 질문은 여러 에이전트에 동시 위임합니다 (예: "내 자산과 예산 현황" → 자산 + 가계부)
- 일반 상담, 인사, 간단한 질문은 에이전트 없이 직접 답변합니다.
- 에이전트에게 위임할 때는 사용자 질문의 핵심을 구체적으로 전달합니다.

## 응답 규칙
- 에이전트 결과를 자연스럽게 종합하여 하나의 응답으로 작성합니다.
- 금액은 ₩ 기호와 천 단위 구분자 사용
- 마크다운 테이블, 리스트 등으로 가독성 높게 정리
- 투자 관련 답변 시 면책 조항 포함
- 한국어로 답변"""


# ── 오케스트레이터 도구 정의 (서브에이전트 위임) ──

ORCHESTRATOR_TOOLS = [
    {
        "type": "function",
        "function": {
            "name": "ask_asset_agent",
            "description": "자산/포트폴리오 관련 질문을 자산 분석 에이전트에게 위임합니다. 보유 자산, 시세, 거래 내역, 수익률, 리밸런싱 관련 질문에 사용합니다.",
            "parameters": {
                "type": "object",
                "properties": {
                    "question": {
                        "type": "string",
                        "description": "자산 에이전트에게 전달할 구체적인 질문",
                    },
                },
                "required": ["question"],
            },
        },
    },
{
        "type": "function",
        "function": {
            "name": "ask_budget_agent",
            "description": "예산/지출/수입 관련 질문을 가계부 에이전트에게 위임합니다. 예산 현황, 지출 분석, 수입 내역, 고정비, 할부금 관련 질문에 사용합니다.",
            "parameters": {
                "type": "object",
                "properties": {
                    "question": {
                        "type": "string",
                        "description": "가계부 에이전트에게 전달할 구체적인 질문",
                    },
                },
                "required": ["question"],
            },
        },
    },
]


# ── 에이전트 인스턴스 ──

_AGENTS: dict[str, SubAgent] = {
    "ask_asset_agent": AssetAgent(),
    "ask_budget_agent": BudgetAgent(),
}


class AgentGraph:
    """오케스트레이터 기반 에이전트 그래프.

    사용자 질문 → 오케스트레이터(라우팅) → 서브에이전트(실행) → 종합 응답(스트리밍)

    Yields:
        {"type": "agent", "name": str, "status": "started"|"done"}
        {"type": "tool", "agent": str, "name": str, "status": "calling"|"done"|"error"}
        {"type": "token", "content": str}
        {"type": "done", "state": dict}
        {"type": "error", "message": str}
    """

    def __init__(self) -> None:
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
        # ── 1. 컨텍스트 구성 ──
        from app.services.chatbot_service import (
            build_financial_context,
            load_user_patterns,
        )

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

        system_prompt = (
            f"{ORCHESTRATOR_PROMPT}\n\n## 사용자 재무 현황\n{financial_context}"
        )
        if investment_prompt:
            system_prompt += f"\n\n## 사용자 투자 철학/전략\n{investment_prompt}"

        # ── 2. LLM 메시지 구성 ──
        llm_messages: list[dict] = [
            {"role": "system", "content": system_prompt},
            *history,
            {"role": "user", "content": query},
        ]

        # ── 3. 오케스트레이터 루프 ──
        agents_called: list[str] = []
        tool_rounds = 0

        try:
            while tool_rounds < MAX_ORCHESTRATOR_ROUNDS:
                response = await acompletion(
                    model=settings.chatbot_model,
                    messages=llm_messages,
                    max_tokens=settings.CHATBOT_MAX_TOKENS,
                    temperature=settings.CHATBOT_TEMPERATURE,
                    tools=ORCHESTRATOR_TOOLS,
                    tool_choice="auto",
                )

                message = response.choices[0].message

                # 서브에이전트 위임이 필요한 경우
                if hasattr(message, "tool_calls") and message.tool_calls:
                    tool_rounds += 1
                    llm_messages.append(message.model_dump())

                    # 순차 실행 (세션 안전성)
                    for tc in message.tool_calls:
                        fn_name = tc.function.name
                        args = (
                            json.loads(tc.function.arguments)
                            if tc.function.arguments
                            else {}
                        )
                        agent = _AGENTS.get(fn_name)

                        if agent:
                            yield {
                                "type": "agent",
                                "name": agent.display_name,
                                "status": "started",
                            }
                            agents_called.append(agent.name)

                            # run_stream으로 도구 호출 이벤트를 실시간 전달
                            agent_content = ""
                            async for sub_event in agent.run_stream(
                                question=args.get("question", query),
                                context=financial_context,
                                db=db,
                                user_id=user_id,
                                market=market,
                            ):
                                if sub_event["type"] == "tool":
                                    yield {
                                        "type": "tool",
                                        "agent": agent.display_name,
                                        "name": sub_event["display_name"],
                                        "status": sub_event["status"],
                                    }
                                elif sub_event["type"] == "result":
                                    agent_content = sub_event["content"]

                            yield {
                                "type": "agent",
                                "name": agent.display_name,
                                "status": "done",
                            }

                            llm_messages.append({
                                "role": "tool",
                                "tool_call_id": tc.id,
                                "content": agent_content,
                            })
                        else:
                            llm_messages.append({
                                "role": "tool",
                                "tool_call_id": tc.id,
                                "content": "알 수 없는 에이전트입니다.",
                            })

                    logger.info(
                        f"[Orchestrator] Round {tool_rounds}: "
                        f"{[tc.function.name for tc in message.tool_calls]}"
                    )
                    # 서브에이전트 실행 완료 → 스트리밍 최종 응답으로 이동
                    # (불필요한 비스트리밍 합성 호출 생략)
                    break

                # 직접 답변 — 아래 스트리밍 섹션에서 처리
                break

        except Exception as e:
            logger.error(f"[Orchestrator] Error: {e}")
            yield {
                "type": "error",
                "message": "AI 응답 생성 중 오류가 발생했습니다.",
            }
            return

        # ── 4. 최종 응답 스트리밍 ──
        # 직접 답변이든 서브에이전트 경유든 항상 스트리밍으로 최종 응답 생성
        yield {"type": "generating"}

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
                    yield {"type": "token", "content": delta.content}

        except Exception as e:
            logger.error(f"[Orchestrator] Stream error: {e}")
            yield {
                "type": "error",
                "message": "AI 응답 생성 중 오류가 발생했습니다.",
            }
            return

        # ── 5. 체크포인트 저장 ──
        store = await self._get_checkpoint_store()
        prev_state = await store.load(conversation_id)

        checkpoint_data = {
            "message_count": ((prev_state or {}).get("message_count", 0)) + 2,
            "tool_rounds": tool_rounds,
            "agents_called": agents_called,
            "last_query": query[:100],
        }
        await store.save(conversation_id, checkpoint_data)

        yield {"type": "done", "state": checkpoint_data}

    def get_agent_info(self) -> list[dict]:
        """사용 가능한 에이전트 정보 반환"""
        return [
            {
                "name": agent.name,
                "display_name": agent.display_name,
                "description": agent.description,
            }
            for agent in _AGENTS.values()
        ]
