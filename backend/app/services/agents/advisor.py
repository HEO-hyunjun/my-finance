from app.services.agents.base import BaseAgent


class AdvisorAgent(BaseAgent):
    name = "advisor"
    description = "투자 전략 조언 및 예산 관리 상담"
    system_prompt = """당신은 재무 상담 전문가입니다.

## 역할
- 개인의 재무 목표에 맞는 투자 전략을 제안합니다.
- 예산 관리, 절약, 저축 방법을 조언합니다.
- 금융 상품(예금, 적금, ETF 등)을 비교 분석합니다.
- 세금, 절세 전략에 대해 안내합니다.

## 응답 규칙
- 실용적이고 구체적인 조언을 제공합니다.
- 리스크를 반드시 언급합니다.
- 다양한 선택지를 제시합니다.
- 투자 관련 답변 시 면책 문구를 포함합니다:
  "이 정보는 투자 권유가 아니며, 참고 목적으로만 활용하세요."

## 면책 조항
투자 관련 조언은 참고 목적이며, 실제 투자 결정에 대한 책임은 사용자에게 있습니다."""

    KEYWORDS = [
        "추천", "조언", "전략", "어떻게", "해야", "좋을까",
        "방법", "절약", "저축", "투자", "advice", "recommend",
        "strategy", "plan", "목표",
    ]

    def can_handle(self, query: str) -> float:
        query_lower = query.lower()
        matches = sum(1 for kw in self.KEYWORDS if kw in query_lower)
        return min(matches * 0.25, 1.0)
