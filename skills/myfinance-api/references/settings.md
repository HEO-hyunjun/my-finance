# 설정 — 투자 프롬프트

## 투자 프롬프트 조회
- **URL**: `GET /api/v1/settings/investment-prompt`
- **설명**: 사용자가 설정한 투자 전략/성향 프롬프트를 조회한다. AI 인사이트나 챗봇이 이 프롬프트를 참조하여 개인화된 투자 조언을 생성한다.
- **응답**: `InvestmentPromptResponse` (200)
- **응답 필드**:
  | 필드 | 타입 | 설명 |
  |------|------|------|
  | investment_prompt | string? | 투자 전략 프롬프트 (null이면 미설정) |
  | updated_at | datetime? | 마지막 수정 시각 |
- **예시**:
  ```bash
  curl "${MYFINANCE_BASE_URL}/api/v1/settings/investment-prompt" \
    -H "X-API-Key: ${MYFINANCE_API_KEY}"
  ```
- **응답 예시**:
  ```json
  {
    "investment_prompt": "30대 초반, 공격적 투자 성향. 국내주식 40%, 미국주식 30%, 채권 20%, 현금 10% 목표 비중. 월 200만원 투자 가능.",
    "updated_at": "2026-03-15T10:30:00"
  }
  ```
