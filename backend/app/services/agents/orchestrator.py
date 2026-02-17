import logging

from app.services.agents.analyzer import AnalyzerAgent
from app.services.agents.advisor import AdvisorAgent
from app.services.agents.fetcher import FetcherAgent
from app.services.agents.researcher import ResearcherAgent

logger = logging.getLogger(__name__)


class AgentOrchestrator:
    """서브에이전트 라우터/오케스트레이터.

    사용자 쿼리를 분석하여 가장 적합한 에이전트를 선택하고 실행합니다.
    복합적인 질문의 경우 여러 에이전트를 순차적으로 실행합니다.
    """

    def __init__(self):
        self.agents = [
            ResearcherAgent(),
            FetcherAgent(),
            AnalyzerAgent(),
            AdvisorAgent(),
        ]

    async def route_and_execute(
        self,
        query: str,
        context: dict | None = None,
    ) -> dict:
        """쿼리를 분석하여 최적 에이전트에 라우팅"""

        # Score each agent
        scores = []
        for agent in self.agents:
            score = agent.can_handle(query)
            scores.append((agent, score))
            logger.debug(f"Agent {agent.name}: score={score:.2f}")

        # Sort by score descending
        scores.sort(key=lambda x: x[1], reverse=True)

        best_agent, best_score = scores[0]

        # If best score is too low, use general advisor as fallback
        if best_score < 0.25:
            best_agent = self.agents[2]  # AdvisorAgent as default

        logger.info(f"Routing to agent: {best_agent.name} (score={best_score:.2f})")

        result = await best_agent.run(query, context)
        result["routing_score"] = best_score

        return result

    def get_agent_info(self) -> list[dict]:
        """등록된 에이전트 정보 반환"""
        return [
            {"name": a.name, "description": a.description}
            for a in self.agents
        ]
