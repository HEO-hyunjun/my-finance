"""서브에이전트 기본 클래스.

각 서브에이전트는 특정 도메인의 도구를 가지고 ReAct 루프를 실행합니다.
오케스트레이터에 의해 호출됩니다.
"""

import json
import logging
import uuid
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Any

from litellm import acompletion
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.services.market_service import MarketService

logger = logging.getLogger(__name__)


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

    async def run(
        self,
        question: str,
        context: str,
        db: AsyncSession,
        user_id: uuid.UUID,
        market: MarketService,
    ) -> SubAgentResult:
        """서브에이전트 실행 (ReAct 루프)"""

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

                # 도구 호출이 있으면 실행 후 다음 라운드
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

                        try:
                            result = await self.execute_tool(
                                fn_name, args, db, user_id, market,
                            )
                        except Exception as e:
                            logger.warning(f"[{self.name}] Tool {fn_name} failed: {e}")
                            result = {"error": str(e)}

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
                return SubAgentResult(
                    content=message.content or "",
                    tools_used=tools_used,
                )

            # max rounds 도달 → 마지막 응답 생성
            final = await acompletion(
                model=settings.chatbot_model,
                messages=messages,
                max_tokens=1024,
                temperature=0.3,
            )
            return SubAgentResult(
                content=final.choices[0].message.content or "",
                tools_used=tools_used,
            )

        except Exception as e:
            logger.error(f"[{self.name}] Error: {e}")
            return SubAgentResult(
                content=f"분석 중 오류가 발생했습니다: {e}",
                tools_used=tools_used,
                success=False,
            )
