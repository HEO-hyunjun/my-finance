from app.services.agents.base import BaseAgent


class AnalyzerAgent(BaseAgent):
    name = "analyzer"
    description = "자산 포트폴리오 분석 및 리밸런싱 제안"
    system_prompt = """당신은 자산 분석 전문가입니다.

## 역할
- 포트폴리오 구성을 분석하고 다각화 정도를 평가합니다.
- 자산 배분 비율의 적정성을 판단합니다.
- 리밸런싱 필요성과 구체적 방안을 제시합니다.
- 수익률, 변동성, 리스크를 종합적으로 평가합니다.

## 응답 규칙
- 수치 기반 분석을 제공합니다.
- 자산 비율은 퍼센트로, 금액은 원화로 표시합니다.
- 장단점을 균형있게 제시합니다.
- 분석 근거를 명확히 설명합니다."""

    KEYWORDS = [
        "분석", "포트폴리오", "비중", "배분", "리밸런싱",
        "수익률", "변동성", "리스크", "analyze", "portfolio",
        "allocation", "diversi",
    ]

    def can_handle(self, query: str) -> float:
        query_lower = query.lower()
        matches = sum(1 for kw in self.KEYWORDS if kw in query_lower)
        return min(matches * 0.25, 1.0)
