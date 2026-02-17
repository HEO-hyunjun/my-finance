import json
import logging
from abc import ABC, abstractmethod

from litellm import acompletion
from app.core.config import settings

logger = logging.getLogger(__name__)


class BaseAgent(ABC):
    """서브에이전트 기본 클래스"""

    name: str = "base"
    description: str = ""
    system_prompt: str = ""
    tool_definitions: list[dict] = []  # LiteLLM function calling tools

    async def run(
        self,
        query: str,
        context: dict | None = None,
        tools_context: dict | None = None,
    ) -> dict:
        """에이전트 실행: query + context -> result

        Args:
            query: 사용자 질문
            context: 재무 컨텍스트 등 추가 정보
            tools_context: tool 실행에 필요한 서비스 인스턴스 (예: market, news)
        """
        messages = [
            {"role": "system", "content": self._build_system_prompt(context)},
            {"role": "user", "content": query},
        ]

        kwargs: dict = {
            "model": settings.chatbot_model,
            "messages": messages,
            "max_tokens": 1024,
            "temperature": 0.5,
        }

        if self.tool_definitions:
            kwargs["tools"] = self.tool_definitions
            kwargs["tool_choice"] = "auto"

        try:
            response = await acompletion(**kwargs)
            message = response.choices[0].message

            # Tool call 처리: LLM이 도구 호출을 요청한 경우
            if hasattr(message, "tool_calls") and message.tool_calls:
                tool_results = await self._execute_tools(
                    message.tool_calls, tools_context or {}
                )
                messages.append(message.model_dump())
                messages.extend(tool_results)

                # Tool 결과를 포함하여 최종 응답 생성
                final_response = await acompletion(
                    model=settings.chatbot_model,
                    messages=messages,
                    max_tokens=1024,
                    temperature=0.5,
                )
                content = final_response.choices[0].message.content
            else:
                content = message.content

            return {"agent": self.name, "result": content, "success": True}
        except Exception as e:
            logger.warning(f"Agent {self.name} failed: {e}")
            return {"agent": self.name, "result": str(e), "success": False}

    async def _execute_tools(
        self, tool_calls: list, tools_context: dict
    ) -> list[dict]:
        """Tool call 실행. 서브클래스에서 오버라이드하여 실제 도구 호출 처리."""
        return []

    def _build_system_prompt(self, context: dict | None = None) -> str:
        prompt = self.system_prompt
        if context:
            prompt += f"\n\n## 컨텍스트\n```json\n{json.dumps(context, ensure_ascii=False, default=str)}\n```"
        return prompt

    @abstractmethod
    def can_handle(self, query: str) -> float:
        """이 에이전트가 해당 쿼리를 처리할 수 있는 적합도 (0.0~1.0)"""
        pass
