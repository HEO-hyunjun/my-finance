# Plan: Chatbot (AI 재무 상담 챗봇)

> **Feature**: chatbot
> **Created**: 2026-02-15
> **PRD Reference**: AI 기반 투자 상담, 재무 질의응답
> **PDCA Phase**: Plan

---

## 1. 기능 개요

사용자의 자산/예산/거래 데이터를 기반으로 맞춤형 AI 재무 상담을 제공하는 대화형 챗봇. LiteLLM을 통해 다양한 LLM 프로바이더를 지원하며, LangChain을 활용해 사용자 데이터 컨텍스트를 주입한 지능형 응답을 생성한다.

### 1.1 핵심 목표

- 사용자 재무 데이터 기반 맞춤형 AI 상담 (자산 분석, 예산 조언)
- 실시간 대화형 인터페이스 (채팅 UI + 스트리밍 응답)
- 포트폴리오 분석 및 투자 인사이트 제공
- 예산 소비 패턴 분석 및 절약 팁
- 대화 히스토리 관리 (세션 기반)

### 1.2 기존 구현 피처 연계

| 연계 피처 | 활용 데이터 | API |
|-----------|-------------|-----|
| asset-management | 자산 목록, 보유 현황, 요약 | `GET /api/v1/assets/summary` |
| budget-management | 예산 요약, 지출 현황 | `GET /api/v1/budget/summary` |
| dashboard | 통합 재무 데이터 | `GET /api/v1/dashboard/summary` |
| transactions | 거래 내역 | `GET /api/v1/transactions` |
| market | 환율, 시세 정보 | `GET /api/v1/market/*` |
| news | 금융 뉴스 | `GET /api/v1/news` |

---

## 2. 구현 범위

### 2.1 In Scope (이번 Plan)

#### 채팅 기능

- [ ] **대화형 AI 상담**: 자연어로 재무 질문 → AI 응답
- [ ] **스트리밍 응답**: SSE(Server-Sent Events) 기반 실시간 토큰 스트리밍
- [ ] **대화 히스토리**: 세션 내 대화 맥락 유지 (최대 20턴)
- [ ] **사전 정의 질문**: 빠른 시작을 위한 추천 질문 버튼
- [ ] **마크다운 렌더링**: AI 응답 내 마크다운 포맷 지원

#### 컨텍스트 주입 (사용자 데이터 기반)

- [ ] **자산 컨텍스트**: 현재 보유 자산 요약을 system prompt에 포함
- [ ] **예산 컨텍스트**: 이번 달 예산/지출 현황 포함
- [ ] **시장 컨텍스트**: 최신 환율/시세 정보 포함

#### Backend

- [ ] **`POST /api/v1/chatbot/chat`** — 대화 요청 (스트리밍 응답)
- [ ] **`GET /api/v1/chatbot/conversations`** — 대화 세션 목록 조회
- [ ] **`GET /api/v1/chatbot/conversations/{id}`** — 특정 대화 조회
- [ ] **`DELETE /api/v1/chatbot/conversations/{id}`** — 대화 삭제
- [ ] **ChatService**: LangChain + LiteLLM 기반 AI 서비스
- [ ] **대화 저장**: PostgreSQL에 대화 히스토리 저장

#### Frontend

- [ ] **채팅 페이지** (`/chatbot`): 채팅 인터페이스 전체
- [ ] **메시지 컴포넌트**: 사용자/AI 메시지 버블
- [ ] **입력 컴포넌트**: 텍스트 입력 + 전송 버튼
- [ ] **추천 질문**: 자주 묻는 재무 질문 칩
- [ ] **대화 사이드바**: 이전 대화 세션 목록 (선택사항)

### 2.2 Out of Scope (향후 분리)

- RAG 기반 문서 검색 (뉴스/리포트 기반 답변 강화)
- Tool Calling / Function Calling (자동 데이터 조회)
- 음성 입력/출력
- 파일 업로드 (영수증 분석 등)
- 다국어 지원
- AI 추천 알림 (프로액티브 알림)

---

## 3. 기술 설계 방향

### 3.1 AI 아키텍처

```
┌─────────────┐     ┌──────────────┐     ┌──────────────┐
│  Frontend   │────▶│  FastAPI      │────▶│  LangChain   │
│  (Chat UI)  │◀────│  (SSE Stream) │◀────│  + LiteLLM   │
└─────────────┘     └──────┬───────┘     └──────────────┘
                           │
                    ┌──────▼───────┐
                    │  Context     │
                    │  Builder     │
                    ├──────────────┤
                    │ AssetService │
                    │ BudgetService│
                    │ MarketService│
                    │ DashboardSvc │
                    └──────────────┘
```

### 3.2 API 설계

```
POST /api/v1/chatbot/chat
Authorization: Bearer {token}
Content-Type: application/json

Request:
{
  "message": "내 포트폴리오 분석해줘",
  "conversation_id": "uuid-or-null"  // null이면 새 대화
}

Response: text/event-stream (SSE)
data: {"type": "token", "content": "현재"}
data: {"type": "token", "content": " 보유"}
data: {"type": "token", "content": " 자산을"}
...
data: {"type": "done", "conversation_id": "uuid", "message_id": "uuid"}
```

```
GET /api/v1/chatbot/conversations
Authorization: Bearer {token}

Response:
{
  "conversations": [
    {
      "id": "uuid",
      "title": "포트폴리오 분석",
      "last_message_at": "2026-02-15T10:30:00Z",
      "message_count": 8
    }
  ]
}
```

### 3.3 DB 모델

```
conversations (대화 세션)
├── id: UUID (PK)
├── user_id: UUID (FK → users)
├── title: VARCHAR(200)  -- 첫 메시지 기반 자동 생성
├── created_at: TIMESTAMP
└── updated_at: TIMESTAMP

messages (대화 메시지)
├── id: UUID (PK)
├── conversation_id: UUID (FK → conversations)
├── role: VARCHAR(20)  -- 'user' | 'assistant'
├── content: TEXT
├── token_count: INTEGER  -- 토큰 사용량 추적
├── created_at: TIMESTAMP
└── model: VARCHAR(50)  -- 사용된 모델명
```

### 3.4 LangChain + LiteLLM 구성

```python
# LiteLLM을 통한 모델 호출
# 지원 모델: OpenAI GPT-4, Anthropic Claude, etc.
# .env에서 LITELLM_MODEL, API 키 설정

System Prompt 구조:
1. 역할 정의 (재무 상담 전문 AI)
2. 응답 규칙 (한국어, 마크다운, 숫자 포맷)
3. 사용자 재무 컨텍스트 (동적 주입)
   - 총 자산: {total_value_krw}원
   - 자산 분포: {breakdown}
   - 이번 달 예산: {budget_summary}
   - 최근 환율: {exchange_rate}
4. 제한사항 (투자 책임 고지)
```

### 3.5 Backend 아키텍처

```
app/
├── models/
│   └── conversation.py      # Conversation, Message 모델
├── schemas/
│   └── chatbot.py            # ChatRequest, ChatResponse, ConversationList
├── services/
│   └── chatbot_service.py    # ChatService (LangChain + LiteLLM + 컨텍스트)
└── api/v1/endpoints/
    └── chatbot.py            # /api/v1/chatbot 라우터
```

### 3.6 Frontend 아키텍처 (FSD)

```
features/chatbot/
├── api/
│   └── index.ts              # useChatMutation, useConversations
├── model/
│   └── chat-store.ts         # Zustand - 메시지 상태, 스트리밍 상태
├── ui/
│   ├── ChatMessage.tsx       # 메시지 버블 (user/assistant)
│   ├── ChatInput.tsx         # 메시지 입력 + 전송
│   ├── SuggestedQuestions.tsx # 추천 질문 칩
│   ├── ConversationList.tsx  # 이전 대화 목록 (사이드바)
│   └── StreamingText.tsx     # SSE 스트리밍 텍스트 렌더링
└── lib/
    └── sse-client.ts         # SSE 연결 유틸리티

pages/chatbot/
└── index.tsx                 # 채팅 페이지 레이아웃
```

### 3.7 채팅 UI 레이아웃

```
Desktop:
┌─────────────────────────────────────────────────┐
│  ┌──────────┐  ┌──────────────────────────────┐ │
│  │ 대화 목록  │  │       AI 재무 상담            │ │
│  │           │  │                              │ │
│  │ > 대화 1  │  │  [AI] 안녕하세요! 재무 상담    │ │
│  │   대화 2  │  │       AI입니다.               │ │
│  │   대화 3  │  │                              │ │
│  │           │  │  [나] 내 자산 분석해줘         │ │
│  │           │  │                              │ │
│  │           │  │  [AI] 현재 총 자산은...       │ │
│  │           │  │                              │ │
│  │           │  ├──────────────────────────────┤ │
│  │           │  │ 추천: [포트폴리오 분석] [예산] │ │
│  │           │  ├──────────────────────────────┤ │
│  │           │  │ [메시지를 입력하세요...]  [전송]│ │
│  └──────────┘  └──────────────────────────────┘ │
└─────────────────────────────────────────────────┘

Mobile (사이드바 숨김):
┌──────────────────────────┐
│  AI 재무 상담         [≡] │
├──────────────────────────┤
│                          │
│  [AI] 메시지 ...         │
│  [나] 메시지 ...         │
│  [AI] 메시지 ...         │
│                          │
├──────────────────────────┤
│ [포트폴리오] [예산] [시장]│
├──────────────────────────┤
│ [입력...]          [전송] │
└──────────────────────────┘
```

---

## 4. 의존성

### 4.1 선행 조건

| 의존성 | 상태 | 비고 |
|--------|------|------|
| asset-management | 구현 완료 | 자산 컨텍스트 데이터 |
| budget-management | 구현 완료 | 예산 컨텍스트 데이터 |
| dashboard-service | 구현 완료 | 통합 데이터 조회 활용 |
| market API | 구현 완료 | 시세/환율 컨텍스트 |
| Auth (JWT) | 구현 완료 | 사용자별 데이터 접근 |

### 4.2 새로 추가할 의존성

| 패키지 | 용도 | 위치 |
|--------|------|------|
| `litellm` | LLM 프로바이더 통합 게이트웨이 | Backend |
| `langchain` | LLM 체인, 프롬프트 관리 | Backend |
| `langchain-community` | LiteLLM 연동 | Backend |
| `sse-starlette` | FastAPI SSE 스트리밍 | Backend |
| `react-markdown` | AI 응답 마크다운 렌더링 | Frontend |
| `remark-gfm` | GFM 마크다운 지원 | Frontend |

### 4.3 환경 변수 (추가)

```env
# AI Model Configuration
LITELLM_MODEL=gpt-4o-mini          # 기본 모델
OPENAI_API_KEY=sk-...              # OpenAI API Key (또는 다른 프로바이더)
CHATBOT_MAX_TOKENS=2048            # 최대 응답 토큰
CHATBOT_TEMPERATURE=0.7            # 응답 다양성
CHATBOT_MAX_HISTORY=20             # 대화 히스토리 최대 턴 수
```

### 4.4 구현 순서 (권장)

```
Phase 1: Backend — DB 모델 + 스키마
  1. Conversation, Message SQLAlchemy 모델
  2. Alembic migration
  3. Pydantic 스키마 (ChatRequest, ChatResponse, ConversationList)

Phase 2: Backend — AI 서비스
  4. ChatService (LangChain + LiteLLM 연동)
  5. ContextBuilder (사용자 재무 데이터 수집 → system prompt)
  6. SSE 스트리밍 응답 구현

Phase 3: Backend — API 엔드포인트
  7. POST /api/v1/chatbot/chat (스트리밍)
  8. GET /api/v1/chatbot/conversations (목록)
  9. GET /api/v1/chatbot/conversations/{id} (상세)
  10. DELETE /api/v1/chatbot/conversations/{id} (삭제)

Phase 4: Frontend — 상태 관리 + API
  11. chat-store.ts (Zustand - 메시지, 스트리밍 상태)
  12. SSE 클라이언트 유틸리티
  13. TanStack Query hooks (대화 목록)

Phase 5: Frontend — UI 컴포넌트
  14. ChatMessage (메시지 버블 + 마크다운)
  15. ChatInput (입력 + 전송)
  16. SuggestedQuestions (추천 질문 칩)
  17. StreamingText (실시간 텍스트 렌더링)
  18. ConversationList (대화 목록 사이드바)

Phase 6: Frontend — 페이지 조합
  19. pages/chatbot 레이아웃
  20. 반응형 디자인 (모바일: 사이드바 숨김)
  21. API 연동 + 스트리밍 테스트
```

---

## 5. 리스크 및 고려사항

| 리스크 | 영향 | 대응 방안 |
|--------|------|-----------|
| LLM API 비용 | 사용량 비례 과금 | `gpt-4o-mini` 기본 사용, 토큰 제한(2048), 사용량 모니터링 |
| API 키 노출 위험 | 보안 사고 | Backend에서만 API 호출, 프론트엔드 직접 호출 차단 |
| 응답 지연 (LLM 호출) | UX 저하 | SSE 스트리밍으로 체감 지연 최소화 |
| 부정확한 재무 조언 | 사용자 손실 위험 | 면책 고지문 상시 표시, "참고용" 명시 |
| 컨텍스트 토큰 초과 | 응답 실패 | 컨텍스트 크기 제한, 요약 데이터만 주입 |
| 대화 히스토리 DB 증가 | 스토리지 부담 | 오래된 대화 자동 정리(90일), 메시지 수 제한 |
| LiteLLM 프로바이더 장애 | 서비스 중단 | fallback 모델 설정, 에러 시 안내 메시지 |

---

## 6. 성공 기준

- [ ] 사용자가 자연어로 재무 질문 시 AI가 맞춤형 응답 생성
- [ ] SSE 스트리밍으로 실시간 토큰 단위 응답 표시
- [ ] 사용자의 자산/예산 데이터가 AI 응답에 반영됨
- [ ] 대화 히스토리 저장 및 이전 대화 재개 가능
- [ ] 추천 질문 버튼으로 빠른 상담 시작
- [ ] AI 응답 내 마크다운 (테이블, 볼드, 리스트) 정상 렌더링
- [ ] 반응형 레이아웃 (모바일/데스크톱) 정상 동작
- [ ] 면책 고지문 표시 (투자 조언 면책)
- [ ] 첫 응답 토큰 표시까지 < 2초 (스트리밍 시작)
- [ ] 에러 발생 시 사용자 친화적 에러 메시지 표시

---

## 7. 추천 질문 (Suggested Questions)

```
- "내 자산 포트폴리오를 분석해줘"
- "이번 달 예산 사용 현황을 알려줘"
- "투자 포트폴리오 리밸런싱이 필요할까?"
- "이번 달 절약할 수 있는 부분이 있을까?"
- "현재 환율 기준으로 달러 자산 가치는?"
- "예금/적금 만기 일정을 정리해줘"
```

---

## 8. 다음 단계

Plan 승인 후 → `/pdca design chatbot` 로 상세 설계 문서 작성
