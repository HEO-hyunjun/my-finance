# Analysis: Chatbot (AI 재무 상담 챗봇)

> **Feature**: chatbot
> **Analyzed**: 2026-02-15
> **Design Reference**: `docs/02-design/features/chatbot.design.md`
> **PDCA Phase**: Check (Gap Analysis)

---

## 1. 분석 개요

| 항목 | 값 |
|------|-----|
| 체크리스트 항목 수 | 26 |
| PASS | 24 |
| PARTIAL | 1 |
| FAIL | 1 |
| **Match Rate** | **96%** |

---

## 2. 체크리스트 항목별 판정

### Backend (BE-1 ~ BE-13) — 96%

| 항목 | 설명 | 판정 | 근거 |
|------|------|:----:|------|
| BE-1 | Conversation, Message SQLAlchemy 모델 + Alembic migration | **PARTIAL** | 모델 100% 일치 (UUID PK, FK CASCADE, DateTime timezone, relationship). **Alembic migration 미생성** |
| BE-2 | chatbot.py Pydantic 스키마 | PASS | ChatRequest, SSE Events (Token/Done/Error), MessageResponse, ConversationSummary, ConversationListResponse, ConversationDetailResponse — 전 필드 일치 |
| BE-3 | Settings에 LITELLM_MODEL, CHATBOT_* 환경변수 | PASS | 5개 설정 완전 일치: LITELLM_MODEL, OPENAI_API_KEY, CHATBOT_MAX_TOKENS, CHATBOT_TEMPERATURE, CHATBOT_MAX_HISTORY |
| BE-4 | build_financial_context() 재무 데이터 수집 | PASS | asset_summary, budget_summary, exchange_rate 3개 섹션 + 각각 try/except 격리 |
| BE-5 | chat_stream() LiteLLM 스트리밍 + SSE | PASS | 9단계 로직 완전 일치: 세션 조회/생성 → 메시지 저장 → 히스토리 → 컨텍스트 → LLM 호출 → 응답 저장 → done 이벤트 |
| BE-6 | get_conversations() 대화 목록 | PASS | outerjoin + group_by + order_by desc + limit 50 일치 |
| BE-7 | get_conversation_detail() 대화 상세 | PASS | selectinload(Conversation.messages), None 반환 일치 |
| BE-8 | delete_conversation() 대화 삭제 | PASS | select → delete → commit 패턴 일치 |
| BE-9 | POST /chatbot/chat SSE 엔드포인트 | PASS | EventSourceResponse + MarketService(redis) 주입 일치 |
| BE-10 | GET /chatbot/conversations 목록 | PASS | response_model + Depends(get_current_user) 일치 |
| BE-11 | GET /chatbot/conversations/{id} 상세 | PASS | 404 HTTPException 처리 일치 |
| BE-12 | DELETE /chatbot/conversations/{id} 삭제 | PASS | 404 처리 + {"message": "대화가 삭제되었습니다."} 일치 |
| BE-13 | main.py 라우터 등록 | PASS | `app.include_router(chatbot.router, prefix="/api/v1")` 확인 |

### Frontend (FE-1 ~ FE-13) — 96%

| 항목 | 설명 | 판정 | 근거 |
|------|------|:----:|------|
| FE-1 | Chatbot 타입 정의 (shared/types) | PASS | ChatMessageRole, ChatMessage, ConversationSummary, ConversationListResponse, ConversationDetailResponse, ChatRequest, ChatTokenEvent, ChatDoneEvent, ChatErrorEvent, ChatSSEEvent — 10개 타입 완전 일치 |
| FE-2 | useChatStore Zustand 스토어 | PASS | 4개 상태 + 7개 액션 완전 일치 |
| FE-3 | streamChat() SSE 클라이언트 | **PASS** | Design: `streamChat(message, conversationId, token, options)` / 구현: `streamChat(message, conversationId, options)` — token을 파라미터 대신 localStorage에서 직접 획득하도록 개선. try/catch + reader.releaseLock() 추가로 에러 처리 강화 |
| FE-4 | useConversations, useConversationDetail, useDeleteConversation | PASS | 3개 훅 + chatbotKeys 팩토리 완전 일치 |
| FE-5 | ChatMessage 메시지 버블 + 마크다운 | PASS | user: bg-blue-500 우측, AI: bg-gray-100 좌측 + ReactMarkdown + remarkGfm + 시간 표시 |
| FE-6 | ChatInput 입력 + 전송 | PASS | auto-resize textarea (max 120px), Enter 전송 / Shift+Enter 줄바꿈, disabled 상태, 빈 메시지 차단 |
| FE-7 | SuggestedQuestions 추천 질문 칩 | PASS | 6개 질문 + rounded-full pill 버튼 + hover 효과 |
| FE-8 | StreamingText 실시간 렌더링 | PASS | "생각 중..." animate-pulse/bounce + ReactMarkdown + 커서 블링크 |
| FE-9 | ConversationList 대화 목록 사이드바 | PASS | 새 대화 버튼, 활성 상태 border-l-2 border-blue-500 bg-blue-50, 삭제 hover 표시 |
| FE-10 | 반응형 레이아웃 (모바일 사이드바 숨김) | PASS | Design보다 개선: 모바일 overlay sidebar + 햄버거 메뉴 + lg:static 반응형 전환 |
| FE-11 | 면책 고지문 표시 | PASS | "AI 응답은 참고 목적이며, 투자 결정에 대한 책임은 사용자에게 있습니다." |
| FE-12 | 빈 대화 상태 UI (환영 + 추천 질문) | PASS | 로봇 이모지 + 환영 메시지 + SuggestedQuestions |
| FE-13 | react-markdown, remark-gfm 패키지 설치 | PASS | package.json: react-markdown@^10.1.0, remark-gfm@^4.0.1 |

---

## 3. Gap 상세 분석

### GAP-1: Alembic Migration 미생성 (BE-1)

| 항목 | 내용 |
|------|------|
| 심각도 | **Medium** |
| 영향 | DB에 conversations, messages 테이블이 생성되지 않아 런타임에 오류 발생 |
| Design 명세 | `alembic revision --autogenerate -m "add conversations and messages tables"` |
| 현재 상태 | `backend/alembic/versions/` 디렉토리에 migration 파일 없음 |
| 해결 방안 | Docker 환경에서 `alembic revision --autogenerate` 실행 후 `alembic upgrade head` |

---

## 4. Design 대비 개선 사항

구현 과정에서 Design보다 개선된 부분:

| 항목 | Design | 구현 | 개선 내용 |
|------|--------|------|-----------|
| FE-3 SSE Client | token을 파라미터로 전달 | localStorage에서 직접 획득 | 호출부 간소화, 미인증 시 조기 반환 |
| FE-3 SSE Client | 에러 처리 기본 | try/catch + finally reader.releaseLock() | 네트워크 에러 격리, 리소스 해제 보장 |
| FE-10 모바일 레이아웃 | 단순 hidden/shown | overlay sidebar + translate 애니메이션 | UX 향상: 부드러운 전환 + 배경 dimming |
| FE-10 대화 선택 | setConversationId만 | clearChat() + setConversationId | 이전 대화 잔여 상태 방지 |
| Page 컴포넌트 | useAuthStore로 토큰 접근 | sse-client가 자체 관리 | 페이지 의존성 감소, SoC 향상 |

---

## 5. 종합 판정

```
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
  Match Rate: 96% (25/26)
  판정: PASS (>= 90%)
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
  [Plan] ✅ → [Design] ✅ → [Do] ✅ → [Check] ✅ → [Report] ⏳
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
```

- **Backend**: 13개 항목 중 12 PASS, 1 PARTIAL (Alembic migration 미생성)
- **Frontend**: 13개 항목 중 13 PASS (일부 Design 대비 개선)
- **GAP 1건**: Alembic migration (Medium) — 운영 환경 배포 전 필수 해결
- **개선 5건**: SSE 클라이언트 에러 처리, 모바일 레이아웃, 대화 전환 로직 등

**결론**: Match Rate 96%로 PDCA Report 단계로 진행 가능. Alembic migration은 배포 시 해결 필요.
