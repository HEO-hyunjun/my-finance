# Design: Chatbot (AI 재무 상담 챗봇)

> **Feature**: chatbot
> **Created**: 2026-02-15
> **Plan Reference**: `docs/01-plan/features/chatbot.plan.md`
> **PDCA Phase**: Design

---

## 1. Backend 상세 설계

### 1.1 환경 설정

**파일**: `backend/app/core/config.py` (기존 Settings에 추가)

```python
class Settings(BaseSettings):
    # ... 기존 설정 ...

    # AI Chatbot
    LITELLM_MODEL: str = "gpt-4o-mini"
    OPENAI_API_KEY: str = ""
    CHATBOT_MAX_TOKENS: int = 2048
    CHATBOT_TEMPERATURE: float = 0.7
    CHATBOT_MAX_HISTORY: int = 20
```

---

### 1.2 DB 모델

**파일**: `backend/app/models/conversation.py`

```python
import uuid
from datetime import datetime, timezone

from sqlalchemy import String, DateTime, Integer, Text, ForeignKey
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base


class Conversation(Base):
    __tablename__ = "conversations"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
    )
    title: Mapped[str] = mapped_column(String(200), nullable=False, default="새 대화")
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(timezone.utc)
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        onupdate=lambda: datetime.now(timezone.utc),
    )

    messages: Mapped[list["Message"]] = relationship(
        back_populates="conversation", cascade="all, delete-orphan",
        order_by="Message.created_at",
    )


class Message(Base):
    __tablename__ = "messages"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    conversation_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("conversations.id", ondelete="CASCADE"),
        nullable=False,
    )
    role: Mapped[str] = mapped_column(String(20), nullable=False)  # 'user' | 'assistant'
    content: Mapped[str] = mapped_column(Text, nullable=False)
    token_count: Mapped[int] = mapped_column(Integer, nullable=True)
    model: Mapped[str] = mapped_column(String(50), nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(timezone.utc)
    )

    conversation: Mapped["Conversation"] = relationship(back_populates="messages")
```

**Alembic migration**: `alembic revision --autogenerate -m "add conversations and messages tables"`

---

### 1.3 Pydantic 스키마

**파일**: `backend/app/schemas/chatbot.py`

```python
from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel, Field


# --- Request ---

class ChatRequest(BaseModel):
    """채팅 요청"""
    message: str = Field(..., min_length=1, max_length=2000)
    conversation_id: str | None = None  # null이면 새 대화 생성


# --- SSE Event Types ---

class ChatTokenEvent(BaseModel):
    """스트리밍 토큰 이벤트"""
    type: str = "token"
    content: str


class ChatDoneEvent(BaseModel):
    """스트리밍 완료 이벤트"""
    type: str = "done"
    conversation_id: str
    message_id: str


class ChatErrorEvent(BaseModel):
    """에러 이벤트"""
    type: str = "error"
    message: str


# --- Conversation ---

class ConversationSummary(BaseModel):
    """대화 요약 (목록용)"""
    id: str
    title: str
    last_message_at: datetime | None = None
    message_count: int = 0


class ConversationListResponse(BaseModel):
    """대화 목록 응답"""
    conversations: list[ConversationSummary]


class MessageResponse(BaseModel):
    """메시지 응답"""
    id: str
    role: str
    content: str
    created_at: datetime


class ConversationDetailResponse(BaseModel):
    """대화 상세 응답 (메시지 포함)"""
    id: str
    title: str
    messages: list[MessageResponse]
    created_at: datetime
    updated_at: datetime
```

---

### 1.4 서비스 레이어

**파일**: `backend/app/services/chatbot_service.py`

```python
import json
import uuid
from collections.abc import AsyncGenerator
from datetime import datetime, timezone

from litellm import acompletion
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.core.config import settings
from app.models.conversation import Conversation, Message
from app.schemas.chatbot import (
    ChatDoneEvent,
    ChatErrorEvent,
    ChatTokenEvent,
    ConversationDetailResponse,
    ConversationListResponse,
    ConversationSummary,
    MessageResponse,
)
from app.services.asset_service import get_asset_summary
from app.services.budget_service import get_budget_summary
from app.services.market_service import MarketService


# =====================================================
# Context Builder — 사용자 재무 데이터 → system prompt
# =====================================================

SYSTEM_PROMPT_TEMPLATE = """당신은 MyFinance 앱의 AI 재무 상담 전문가입니다.

## 역할
- 사용자의 재무 데이터를 기반으로 맞춤형 상담을 제공합니다.
- 자산 분석, 예산 조언, 포트폴리오 인사이트를 제공합니다.
- 한국어로 응답하며, 금액은 원화(₩) 기준으로 표시합니다.

## 응답 규칙
- 마크다운 형식으로 응답합니다 (테이블, 볼드, 리스트 활용).
- 금액은 천 단위 구분자를 사용합니다 (예: ₩1,234,567).
- 퍼센트는 소수점 2자리까지 표시합니다 (예: +9.04%).
- 간결하고 실용적인 조언을 제공합니다.

## 면책 조항
- 투자 관련 조언은 참고 목적이며, 실제 투자 결정에 대한 책임은 사용자에게 있습니다.
- "이 정보는 투자 권유가 아니며, 참고 목적으로만 활용하세요." 문구를 투자 관련 답변 시 포함합니다.

## 사용자 재무 현황
{financial_context}
"""


async def build_financial_context(
    db: AsyncSession,
    user_id: uuid.UUID,
    market: MarketService,
) -> str:
    """사용자 재무 데이터를 수집하여 컨텍스트 문자열 생성"""
    parts: list[str] = []

    try:
        asset_summary = await get_asset_summary(db, user_id, market)
        parts.append(f"""### 자산 현황
- 총 자산: ₩{asset_summary.total_value_krw:,.0f}
- 총 투자금: ₩{asset_summary.total_invested_krw:,.0f}
- 총 수익/손실: ₩{asset_summary.total_profit_loss:,.0f} ({asset_summary.total_profit_loss_rate:+.2f}%)
- 자산 분포: {json.dumps(asset_summary.breakdown, ensure_ascii=False)}""")
    except Exception:
        parts.append("### 자산 현황\n- 데이터를 불러올 수 없습니다.")

    try:
        budget_summary = await get_budget_summary(db, user_id)
        parts.append(f"""### 예산 현황 (이번 달)
- 총 예산: ₩{budget_summary.total_budget:,.0f}
- 총 지출: ₩{budget_summary.total_spent:,.0f}
- 잔여 예산: ₩{budget_summary.total_remaining:,.0f}
- 사용률: {budget_summary.total_usage_rate:.1f}%""")
    except Exception:
        parts.append("### 예산 현황\n- 데이터를 불러올 수 없습니다.")

    try:
        exchange_rate = await market.get_exchange_rate()
        parts.append(f"""### 시장 정보
- USD/KRW 환율: ₩{exchange_rate.rate:,.2f} (변동: {exchange_rate.change:+.2f})""")
    except Exception:
        parts.append("### 시장 정보\n- 데이터를 불러올 수 없습니다.")

    if not parts:
        return "재무 데이터가 아직 등록되지 않았습니다."

    return "\n\n".join(parts)


# =====================================================
# Conversation CRUD
# =====================================================

async def get_conversations(
    db: AsyncSession,
    user_id: uuid.UUID,
) -> ConversationListResponse:
    """사용자의 대화 목록 조회 (최신순)"""
    stmt = (
        select(
            Conversation.id,
            Conversation.title,
            Conversation.updated_at,
            func.count(Message.id).label("message_count"),
        )
        .outerjoin(Message)
        .where(Conversation.user_id == user_id)
        .group_by(Conversation.id)
        .order_by(Conversation.updated_at.desc())
        .limit(50)
    )
    result = await db.execute(stmt)
    rows = result.all()

    return ConversationListResponse(
        conversations=[
            ConversationSummary(
                id=str(row.id),
                title=row.title,
                last_message_at=row.updated_at,
                message_count=row.message_count,
            )
            for row in rows
        ]
    )


async def get_conversation_detail(
    db: AsyncSession,
    user_id: uuid.UUID,
    conversation_id: uuid.UUID,
) -> ConversationDetailResponse | None:
    """특정 대화 상세 조회 (메시지 포함)"""
    stmt = (
        select(Conversation)
        .options(selectinload(Conversation.messages))
        .where(
            Conversation.id == conversation_id,
            Conversation.user_id == user_id,
        )
    )
    result = await db.execute(stmt)
    conv = result.scalar_one_or_none()

    if not conv:
        return None

    return ConversationDetailResponse(
        id=str(conv.id),
        title=conv.title,
        messages=[
            MessageResponse(
                id=str(m.id),
                role=m.role,
                content=m.content,
                created_at=m.created_at,
            )
            for m in conv.messages
        ],
        created_at=conv.created_at,
        updated_at=conv.updated_at,
    )


async def delete_conversation(
    db: AsyncSession,
    user_id: uuid.UUID,
    conversation_id: uuid.UUID,
) -> bool:
    """대화 삭제"""
    stmt = select(Conversation).where(
        Conversation.id == conversation_id,
        Conversation.user_id == user_id,
    )
    result = await db.execute(stmt)
    conv = result.scalar_one_or_none()

    if not conv:
        return False

    await db.delete(conv)
    await db.commit()
    return True


# =====================================================
# Chat — 스트리밍 AI 응답
# =====================================================

async def chat_stream(
    db: AsyncSession,
    user_id: uuid.UUID,
    message: str,
    conversation_id: str | None,
    market: MarketService,
) -> AsyncGenerator[str, None]:
    """SSE 스트리밍 채팅 응답 생성기"""

    # 1. 대화 세션 조회 또는 생성
    conv: Conversation
    if conversation_id:
        stmt = select(Conversation).options(
            selectinload(Conversation.messages)
        ).where(
            Conversation.id == uuid.UUID(conversation_id),
            Conversation.user_id == user_id,
        )
        result = await db.execute(stmt)
        conv = result.scalar_one_or_none()
        if not conv:
            yield _sse_event(ChatErrorEvent(message="대화를 찾을 수 없습니다."))
            return
    else:
        # 새 대화 생성 — 제목은 첫 메시지의 앞 50자
        conv = Conversation(
            user_id=user_id,
            title=message[:50] + ("..." if len(message) > 50 else ""),
        )
        db.add(conv)
        await db.flush()

    # 2. 사용자 메시지 저장
    user_msg = Message(
        conversation_id=conv.id,
        role="user",
        content=message,
    )
    db.add(user_msg)
    await db.flush()

    # 3. 대화 히스토리 구성 (최대 N턴)
    history = _build_history(conv.messages, settings.CHATBOT_MAX_HISTORY)

    # 4. 재무 컨텍스트 구성
    financial_context = await build_financial_context(db, user_id, market)
    system_prompt = SYSTEM_PROMPT_TEMPLATE.format(financial_context=financial_context)

    # 5. LLM 메시지 구성
    llm_messages = [
        {"role": "system", "content": system_prompt},
        *history,
        {"role": "user", "content": message},
    ]

    # 6. LiteLLM 스트리밍 호출
    full_response = ""
    try:
        response = await acompletion(
            model=settings.LITELLM_MODEL,
            messages=llm_messages,
            max_tokens=settings.CHATBOT_MAX_TOKENS,
            temperature=settings.CHATBOT_TEMPERATURE,
            stream=True,
        )

        async for chunk in response:
            delta = chunk.choices[0].delta
            if delta.content:
                full_response += delta.content
                yield _sse_event(ChatTokenEvent(content=delta.content))

    except Exception as e:
        yield _sse_event(ChatErrorEvent(
            message="AI 응답 생성 중 오류가 발생했습니다. 잠시 후 다시 시도해주세요."
        ))
        return

    # 7. AI 응답 메시지 저장
    assistant_msg = Message(
        conversation_id=conv.id,
        role="assistant",
        content=full_response,
        model=settings.LITELLM_MODEL,
    )
    db.add(assistant_msg)

    # 8. 대화 updated_at 갱신
    conv.updated_at = datetime.now(timezone.utc)
    await db.commit()

    # 9. 완료 이벤트
    yield _sse_event(ChatDoneEvent(
        conversation_id=str(conv.id),
        message_id=str(assistant_msg.id),
    ))


def _build_history(
    messages: list[Message],
    max_turns: int,
) -> list[dict[str, str]]:
    """대화 히스토리를 LLM 메시지 포맷으로 변환 (최근 N턴)"""
    # 최근 max_turns * 2 (user + assistant 쌍)
    recent = messages[-(max_turns * 2):]
    return [{"role": m.role, "content": m.content} for m in recent]


def _sse_event(event: ChatTokenEvent | ChatDoneEvent | ChatErrorEvent) -> str:
    """SSE 이벤트 포맷으로 변환"""
    return f"data: {event.model_dump_json()}\n\n"
```

**핵심 설계 원칙:**
- **ContextBuilder**: 기존 서비스(AssetService, BudgetService, MarketService)를 재활용하여 system prompt에 동적 주입
- **스트리밍**: LiteLLM `acompletion(stream=True)` → AsyncGenerator → SSE 이벤트
- **대화 관리**: PostgreSQL에 Conversation/Message 영속화, 최근 N턴만 LLM에 전달
- **에러 격리**: 재무 데이터 수집 실패 시 해당 섹션만 "불러올 수 없음" 표시, 대화는 계속 가능

---

### 1.5 API 엔드포인트

**파일**: `backend/app/api/v1/endpoints/chatbot.py`

```python
import uuid

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sse_starlette.sse import EventSourceResponse

from app.api.deps import get_current_user
from app.core.database import get_db
from app.core.redis import get_redis
from app.models.user import User
from app.schemas.chatbot import (
    ChatRequest,
    ConversationDetailResponse,
    ConversationListResponse,
)
from app.services.chatbot_service import (
    chat_stream,
    delete_conversation,
    get_conversation_detail,
    get_conversations,
)
from app.services.market_service import MarketService

router = APIRouter(prefix="/chatbot", tags=["Chatbot"])


@router.post("/chat")
async def chat(
    body: ChatRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """AI 채팅 (SSE 스트리밍 응답)"""
    redis = await get_redis()
    market = MarketService(redis)

    return EventSourceResponse(
        chat_stream(
            db=db,
            user_id=current_user.id,
            message=body.message,
            conversation_id=body.conversation_id,
            market=market,
        )
    )


@router.get("/conversations", response_model=ConversationListResponse)
async def list_conversations(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """대화 목록 조회"""
    return await get_conversations(db, current_user.id)


@router.get("/conversations/{conversation_id}", response_model=ConversationDetailResponse)
async def get_conversation(
    conversation_id: str,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """특정 대화 상세 조회"""
    result = await get_conversation_detail(
        db, current_user.id, uuid.UUID(conversation_id)
    )
    if not result:
        raise HTTPException(status_code=404, detail="대화를 찾을 수 없습니다.")
    return result


@router.delete("/conversations/{conversation_id}")
async def remove_conversation(
    conversation_id: str,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """대화 삭제"""
    deleted = await delete_conversation(
        db, current_user.id, uuid.UUID(conversation_id)
    )
    if not deleted:
        raise HTTPException(status_code=404, detail="대화를 찾을 수 없습니다.")
    return {"message": "대화가 삭제되었습니다."}
```

**API 명세:**

```
POST /api/v1/chatbot/chat
  - Auth: Required (JWT Bearer)
  - Request: ChatRequest { message, conversation_id? }
  - Response: text/event-stream (SSE)
    - token: { type: "token", content: "..." }
    - done: { type: "done", conversation_id: "uuid", message_id: "uuid" }
    - error: { type: "error", message: "..." }

GET /api/v1/chatbot/conversations
  - Auth: Required
  - Response: ConversationListResponse

GET /api/v1/chatbot/conversations/{id}
  - Auth: Required
  - Response: ConversationDetailResponse
  - 404: 대화 없음

DELETE /api/v1/chatbot/conversations/{id}
  - Auth: Required
  - 200: { message: "대화가 삭제되었습니다." }
  - 404: 대화 없음
```

**라우터 등록 (`backend/app/main.py`):**

```python
from app.api.v1.endpoints import chatbot

app.include_router(chatbot.router, prefix="/api/v1")
```

---

## 2. Frontend 상세 설계

### 2.1 TypeScript 타입 정의

**파일**: `frontend/src/shared/types/index.ts` (기존 파일 하단에 추가)

```typescript
// ========== Chatbot Types ==========

export type ChatMessageRole = 'user' | 'assistant';

export interface ChatMessage {
  id: string;
  role: ChatMessageRole;
  content: string;
  created_at: string;
}

export interface ConversationSummary {
  id: string;
  title: string;
  last_message_at: string | null;
  message_count: number;
}

export interface ConversationListResponse {
  conversations: ConversationSummary[];
}

export interface ConversationDetailResponse {
  id: string;
  title: string;
  messages: ChatMessage[];
  created_at: string;
  updated_at: string;
}

export interface ChatRequest {
  message: string;
  conversation_id?: string | null;
}

// SSE Event Types
export interface ChatTokenEvent {
  type: 'token';
  content: string;
}

export interface ChatDoneEvent {
  type: 'done';
  conversation_id: string;
  message_id: string;
}

export interface ChatErrorEvent {
  type: 'error';
  message: string;
}

export type ChatSSEEvent = ChatTokenEvent | ChatDoneEvent | ChatErrorEvent;
```

---

### 2.2 Zustand 상태 관리

**파일**: `frontend/src/features/chatbot/model/chat-store.ts`

```typescript
import { create } from 'zustand';
import type { ChatMessage } from '@/shared/types';

interface ChatState {
  // 현재 대화
  conversationId: string | null;
  messages: ChatMessage[];
  isStreaming: boolean;
  streamingContent: string;  // 현재 스트리밍 중인 AI 응답

  // Actions
  setConversationId: (id: string | null) => void;
  setMessages: (messages: ChatMessage[]) => void;
  addUserMessage: (content: string) => void;
  startStreaming: () => void;
  appendStreamToken: (token: string) => void;
  finishStreaming: (messageId: string) => void;
  clearChat: () => void;
}

export const useChatStore = create<ChatState>((set, get) => ({
  conversationId: null,
  messages: [],
  isStreaming: false,
  streamingContent: '',

  setConversationId: (id) => set({ conversationId: id }),

  setMessages: (messages) => set({ messages }),

  addUserMessage: (content) => {
    const userMsg: ChatMessage = {
      id: `temp-${Date.now()}`,
      role: 'user',
      content,
      created_at: new Date().toISOString(),
    };
    set((state) => ({ messages: [...state.messages, userMsg] }));
  },

  startStreaming: () => set({ isStreaming: true, streamingContent: '' }),

  appendStreamToken: (token) =>
    set((state) => ({ streamingContent: state.streamingContent + token })),

  finishStreaming: (messageId) => {
    const { streamingContent, messages } = get();
    const aiMsg: ChatMessage = {
      id: messageId,
      role: 'assistant',
      content: streamingContent,
      created_at: new Date().toISOString(),
    };
    set({
      messages: [...messages, aiMsg],
      isStreaming: false,
      streamingContent: '',
    });
  },

  clearChat: () => set({
    conversationId: null,
    messages: [],
    isStreaming: false,
    streamingContent: '',
  }),
}));
```

---

### 2.3 SSE 클라이언트 유틸리티

**파일**: `frontend/src/features/chatbot/lib/sse-client.ts`

```typescript
import type { ChatSSEEvent } from '@/shared/types';

interface SSEOptions {
  onToken: (content: string) => void;
  onDone: (conversationId: string, messageId: string) => void;
  onError: (message: string) => void;
}

/**
 * SSE 기반 채팅 스트리밍 요청
 * fetch + ReadableStream으로 SSE 파싱
 */
export async function streamChat(
  message: string,
  conversationId: string | null,
  token: string,
  options: SSEOptions,
): Promise<void> {
  const response = await fetch('/api/v1/chatbot/chat', {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
      Authorization: `Bearer ${token}`,
    },
    body: JSON.stringify({
      message,
      conversation_id: conversationId,
    }),
  });

  if (!response.ok) {
    options.onError('서버 연결에 실패했습니다.');
    return;
  }

  const reader = response.body?.getReader();
  if (!reader) {
    options.onError('스트리밍을 시작할 수 없습니다.');
    return;
  }

  const decoder = new TextDecoder();
  let buffer = '';

  while (true) {
    const { done, value } = await reader.read();
    if (done) break;

    buffer += decoder.decode(value, { stream: true });
    const lines = buffer.split('\n');
    buffer = lines.pop() || '';

    for (const line of lines) {
      if (line.startsWith('data: ')) {
        try {
          const event: ChatSSEEvent = JSON.parse(line.slice(6));
          switch (event.type) {
            case 'token':
              options.onToken(event.content);
              break;
            case 'done':
              options.onDone(event.conversation_id, event.message_id);
              return;
            case 'error':
              options.onError(event.message);
              return;
          }
        } catch {
          // JSON 파싱 실패 — 무시
        }
      }
    }
  }
}
```

---

### 2.4 TanStack Query Hooks

**파일**: `frontend/src/features/chatbot/api/index.ts`

```typescript
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { apiClient } from '@/shared/api/client';
import type {
  ConversationListResponse,
  ConversationDetailResponse,
} from '@/shared/types';

export const chatbotKeys = {
  all: ['chatbot'] as const,
  conversations: () => [...chatbotKeys.all, 'conversations'] as const,
  conversation: (id: string) => [...chatbotKeys.all, 'conversation', id] as const,
};

export function useConversations() {
  return useQuery({
    queryKey: chatbotKeys.conversations(),
    queryFn: async (): Promise<ConversationListResponse> => {
      const { data } = await apiClient.get('/v1/chatbot/conversations');
      return data;
    },
  });
}

export function useConversationDetail(id: string | null) {
  return useQuery({
    queryKey: chatbotKeys.conversation(id || ''),
    queryFn: async (): Promise<ConversationDetailResponse> => {
      const { data } = await apiClient.get(`/v1/chatbot/conversations/${id}`);
      return data;
    },
    enabled: !!id,
  });
}

export function useDeleteConversation() {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: async (id: string) => {
      await apiClient.delete(`/v1/chatbot/conversations/${id}`);
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: chatbotKeys.conversations() });
    },
  });
}
```

---

### 2.5 UI 컴포넌트 설계

#### 2.5.1 컴포넌트 트리

```
pages/chatbot/index.tsx
├── ConversationList          # 대화 목록 사이드바 (desktop)
│   └── ConversationItem      # 개별 대화 항목
├── ChatArea                  # 메인 채팅 영역
│   ├── ChatMessage           # 개별 메시지 버블
│   │   └── MarkdownRenderer  # react-markdown 래퍼
│   ├── StreamingText         # 현재 스트리밍 중인 AI 응답
│   ├── SuggestedQuestions    # 추천 질문 칩 (빈 대화 시)
│   ├── ChatInput             # 텍스트 입력 + 전송 버튼
│   └── Disclaimer            # 면책 고지
```

#### 2.5.2 컴포넌트 상세

**ChatMessage** — `features/chatbot/ui/ChatMessage.tsx`

```
사용자 메시지 (오른쪽 정렬):
                                    ┌─────────────────┐
                                    │ 내 자산 분석해줘  │
                                    └─────────────────┘

AI 메시지 (왼쪽 정렬):
┌──────────────────────────────────────────┐
│ 🤖  현재 총 자산은 ₩52,340,000입니다.    │
│                                          │
│ | 자산 유형 | 비중 | 금액 |               │
│ |---------|------|------|               │
│ | 국내주식 | 28.7%| ₩15M |               │
│ | 미국주식 | 38.2%| ₩20M |               │
│ ...                                      │
└──────────────────────────────────────────┘
```

- Props: `message: ChatMessage`
- 사용자 메시지: `bg-blue-500 text-white` 오른쪽 정렬
- AI 메시지: `bg-gray-100` 왼쪽 정렬, react-markdown으로 렌더링
- 시간: `text-xs text-gray-400` 메시지 하단

**ChatInput** — `features/chatbot/ui/ChatInput.tsx`

```
┌────────────────────────────────────────────────────┐
│ [재무 질문을 입력하세요...]              [전송 아이콘] │
└────────────────────────────────────────────────────┘
```

- Props: `onSend: (message: string) => void, disabled: boolean`
- `textarea` (auto-resize, max 4줄)
- Enter로 전송, Shift+Enter로 줄바꿈
- 스트리밍 중 `disabled=true` + 전송 버튼 비활성화
- 빈 메시지 전송 방지

**SuggestedQuestions** — `features/chatbot/ui/SuggestedQuestions.tsx`

```
┌──────────────────────────────────────────────────────┐
│  [내 포트폴리오 분석] [이번 달 예산 현황]               │
│  [리밸런싱 필요?] [절약 팁] [환율 기준 달러 자산]       │
└──────────────────────────────────────────────────────┘
```

- Props: `onSelect: (question: string) => void`
- 메시지가 없을 때만 표시 (새 대화 시작 시)
- 클릭 시 `onSelect(question)` → `onSend()` 트리거

**StreamingText** — `features/chatbot/ui/StreamingText.tsx`

- Props: `content: string` (from `useChatStore.streamingContent`)
- react-markdown으로 실시간 렌더링
- 끝에 깜빡이는 커서 `▊` 애니메이션
- `isStreaming` 중일 때만 표시

**ConversationList** — `features/chatbot/ui/ConversationList.tsx`

```
┌──────────────────┐
│  새 대화  [+]     │
│──────────────────│
│ > 포트폴리오 분석  │
│   예산 상담       │
│   달러 자산 환산   │
│──────────────────│
│  총 3개 대화      │
└──────────────────┘
```

- Props: `conversations`, `activeId`, `onSelect`, `onNew`, `onDelete`
- 활성 대화: `bg-blue-50 border-l-2 border-blue-500`
- 삭제: 아이콘 hover 시 표시 → confirm 후 삭제

---

### 2.6 페이지 레이아웃

**파일**: `frontend/src/pages/chatbot/index.tsx`

```typescript
import { useState } from 'react';
import { useConversations, useConversationDetail } from '@/features/chatbot/api';
import { useChatStore } from '@/features/chatbot/model/chat-store';
import { streamChat } from '@/features/chatbot/lib/sse-client';
import { useAuthStore } from '@/features/auth/model/auth-store';
import { ChatMessage } from '@/features/chatbot/ui/ChatMessage';
import { ChatInput } from '@/features/chatbot/ui/ChatInput';
import { SuggestedQuestions } from '@/features/chatbot/ui/SuggestedQuestions';
import { StreamingText } from '@/features/chatbot/ui/StreamingText';
import { ConversationList } from '@/features/chatbot/ui/ConversationList';

export function Component() {
  const [sidebarOpen, setSidebarOpen] = useState(false);
  const { data: convData } = useConversations();
  const token = useAuthStore((s) => s.accessToken);

  const {
    conversationId, messages, isStreaming, streamingContent,
    setConversationId, setMessages, addUserMessage,
    startStreaming, appendStreamToken, finishStreaming, clearChat,
  } = useChatStore();

  const handleSend = async (text: string) => {
    if (!token || isStreaming) return;
    addUserMessage(text);
    startStreaming();

    await streamChat(text, conversationId, token, {
      onToken: appendStreamToken,
      onDone: (convId, msgId) => {
        setConversationId(convId);
        finishStreaming(msgId);
      },
      onError: (msg) => {
        // 에러 시 스트리밍 종료 + 에러 메시지 표시
        finishStreaming(`error-${Date.now()}`);
      },
    });
  };

  const handleNewChat = () => {
    clearChat();
  };

  const handleSelectConversation = (id: string) => {
    setConversationId(id);
    // useConversationDetail로 메시지 로드 후 setMessages
  };

  return (
    <div className="flex h-[calc(100vh-4rem)]">
      {/* Sidebar — desktop only */}
      <aside className="hidden lg:flex w-64 flex-col border-r bg-gray-50">
        <ConversationList
          conversations={convData?.conversations || []}
          activeId={conversationId}
          onSelect={handleSelectConversation}
          onNew={handleNewChat}
        />
      </aside>

      {/* Main Chat Area */}
      <main className="flex-1 flex flex-col">
        {/* Header */}
        <header className="flex items-center justify-between px-4 py-3 border-b">
          <h1 className="text-lg font-bold">AI 재무 상담</h1>
          <button
            className="lg:hidden"
            onClick={() => setSidebarOpen(!sidebarOpen)}
          >
            ☰
          </button>
        </header>

        {/* Messages */}
        <div className="flex-1 overflow-y-auto p-4 space-y-4">
          {messages.length === 0 && !isStreaming && (
            <>
              <div className="text-center text-gray-500 mt-20">
                <p className="text-4xl mb-4">🤖</p>
                <p className="text-lg font-medium">AI 재무 상담에 오신 것을 환영합니다</p>
                <p className="text-sm mt-1">자산, 예산, 투자에 대해 무엇이든 물어보세요</p>
              </div>
              <SuggestedQuestions onSelect={handleSend} />
            </>
          )}

          {messages.map((msg) => (
            <ChatMessage key={msg.id} message={msg} />
          ))}

          {isStreaming && (
            <StreamingText content={streamingContent} />
          )}
        </div>

        {/* Disclaimer */}
        <div className="px-4 py-1">
          <p className="text-xs text-gray-400 text-center">
            AI 응답은 참고 목적이며, 투자 결정에 대한 책임은 사용자에게 있습니다.
          </p>
        </div>

        {/* Input */}
        <div className="p-4 border-t">
          <ChatInput onSend={handleSend} disabled={isStreaming} />
        </div>
      </main>
    </div>
  );
}
```

**반응형 레이아웃:**

| 뷰포트 | 레이아웃 | 설명 |
|---------|----------|------|
| Mobile (< 1024px) | 채팅만 표시 | 사이드바 숨김, 햄버거 메뉴로 토글 |
| Desktop (>= 1024px) | 사이드바 + 채팅 | 좌측 256px 사이드바 + 우측 채팅 |

---

## 3. 구현 순서 (Implementation Order)

```
Step 1: Backend — 환경 설정 + DB 모델
  ├── backend/app/core/config.py               (Settings 추가: LITELLM_MODEL 등)
  ├── backend/app/models/conversation.py       (Conversation, Message 모델)
  └── alembic migration                        (conversations, messages 테이블)

Step 2: Backend — 스키마
  └── backend/app/schemas/chatbot.py           (ChatRequest, SSE Events, Conversation 응답)

Step 3: Backend — 서비스
  └── backend/app/services/chatbot_service.py  (ContextBuilder, CRUD, chat_stream)

Step 4: Backend — API 엔드포인트 + 등록
  ├── backend/app/api/v1/endpoints/chatbot.py  (4개 엔드포인트)
  └── backend/app/main.py                      (라우터 등록)

Step 5: Frontend — 타입 정의
  └── frontend/src/shared/types/index.ts       (Chatbot 타입 추가)

Step 6: Frontend — 상태 관리 + SSE 유틸
  ├── frontend/src/features/chatbot/model/chat-store.ts (Zustand)
  └── frontend/src/features/chatbot/lib/sse-client.ts   (SSE fetch)

Step 7: Frontend — API Hooks
  └── frontend/src/features/chatbot/api/index.ts (TanStack Query)

Step 8: Frontend — UI 컴포넌트
  ├── features/chatbot/ui/ChatMessage.tsx       (메시지 버블 + 마크다운)
  ├── features/chatbot/ui/ChatInput.tsx         (입력 + 전송)
  ├── features/chatbot/ui/SuggestedQuestions.tsx (추천 질문)
  ├── features/chatbot/ui/StreamingText.tsx     (스트리밍 렌더링)
  └── features/chatbot/ui/ConversationList.tsx  (대화 목록)

Step 9: Frontend — 페이지 조합
  └── frontend/src/pages/chatbot/index.tsx     (전체 레이아웃)

Step 10: 통합
  ├── npm install react-markdown remark-gfm    (프론트 패키지)
  ├── pip install litellm langchain sse-starlette (백엔드 패키지)
  └── API 연동 + 스트리밍 테스트
```

---

## 4. 에러 처리 전략

### 4.1 Backend

| 상황 | 처리 |
|------|------|
| LLM API 호출 실패 | SSE error 이벤트 전송, "AI 응답 생성 중 오류" 메시지 |
| LLM API 키 미설정 | 서버 시작 시 경고 로그, 호출 시 적절한 에러 반환 |
| 재무 컨텍스트 수집 실패 | 해당 섹션 "불러올 수 없음" 표시, 대화는 계속 가능 |
| 대화 미존재 (잘못된 ID) | 404 Not Found 또는 SSE error 이벤트 |
| 토큰 한도 초과 | LiteLLM 자체 처리 (max_tokens 설정으로 제한) |
| DB 저장 실패 | SSE error 이벤트, 트랜잭션 롤백 |

### 4.2 Frontend

| 상황 | 처리 |
|------|------|
| SSE 연결 실패 | "서버 연결에 실패했습니다" 에러 메시지 |
| 스트리밍 중 끊김 | 현재까지 받은 텍스트 표시 + 에러 안내 |
| 네트워크 오프라인 | 전송 버튼 비활성화 + "인터넷 연결을 확인해주세요" |
| 빈 메시지 전송 시도 | ChatInput에서 차단 (전송 불가) |
| 대화 로딩 실패 | 재시도 버튼 표시 |

---

## 5. 검증 체크리스트

Design → Do 전환 시 구현 검증 기준:

- [ ] **BE-1**: `Conversation`, `Message` SQLAlchemy 모델 + Alembic migration
- [ ] **BE-2**: `chatbot.py` Pydantic 스키마 (ChatRequest, SSE Events, Conversation 응답)
- [ ] **BE-3**: `Settings`에 LITELLM_MODEL, CHATBOT_* 환경변수 추가
- [ ] **BE-4**: `chatbot_service.build_financial_context()` — 재무 데이터 수집
- [ ] **BE-5**: `chatbot_service.chat_stream()` — LiteLLM 스트리밍 + SSE 생성
- [ ] **BE-6**: `chatbot_service.get_conversations()` — 대화 목록 조회
- [ ] **BE-7**: `chatbot_service.get_conversation_detail()` — 대화 상세 + 메시지
- [ ] **BE-8**: `chatbot_service.delete_conversation()` — 대화 삭제
- [ ] **BE-9**: `POST /api/v1/chatbot/chat` SSE 스트리밍 엔드포인트
- [ ] **BE-10**: `GET /api/v1/chatbot/conversations` 대화 목록 엔드포인트
- [ ] **BE-11**: `GET /api/v1/chatbot/conversations/{id}` 대화 상세 엔드포인트
- [ ] **BE-12**: `DELETE /api/v1/chatbot/conversations/{id}` 대화 삭제 엔드포인트
- [ ] **BE-13**: `main.py`에 chatbot 라우터 등록
- [ ] **FE-1**: Chatbot 타입 정의 (`shared/types`)
- [ ] **FE-2**: `useChatStore` Zustand 스토어 (메시지, 스트리밍 상태)
- [ ] **FE-3**: `streamChat()` SSE 클라이언트 유틸리티
- [ ] **FE-4**: `useConversations`, `useConversationDetail`, `useDeleteConversation` hooks
- [ ] **FE-5**: `ChatMessage` — 사용자/AI 메시지 버블 + 마크다운 렌더링
- [ ] **FE-6**: `ChatInput` — 입력 + 전송 (Enter/Shift+Enter 구분)
- [ ] **FE-7**: `SuggestedQuestions` — 추천 질문 칩
- [ ] **FE-8**: `StreamingText` — 실시간 스트리밍 텍스트 + 커서
- [ ] **FE-9**: `ConversationList` — 대화 목록 사이드바
- [ ] **FE-10**: 채팅 페이지 반응형 레이아웃 (모바일: 사이드바 숨김)
- [ ] **FE-11**: 면책 고지문 표시
- [ ] **FE-12**: 빈 대화 상태 UI (환영 메시지 + 추천 질문)
- [ ] **FE-13**: react-markdown, remark-gfm 패키지 설치

---

## 6. 다음 단계

Design 승인 후 → `/pdca do chatbot` 로 구현 시작
