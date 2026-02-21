from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel, Field


# --- Request ---


class ChatRequest(BaseModel):
    """채팅 요청"""

    message: str = Field(..., min_length=1, max_length=2000)
    conversation_id: str | None = None


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


class ChatAgentEvent(BaseModel):
    """서브에이전트 상태 이벤트"""

    type: str = "agent"
    name: str
    status: str  # "started" | "done"


class ChatErrorEvent(BaseModel):
    """에러 이벤트"""

    type: str = "error"
    message: str


# --- Conversation ---


class MessageResponse(BaseModel):
    """메시지 응답"""

    id: str
    role: str
    content: str
    created_at: datetime


class ConversationSummary(BaseModel):
    """대화 요약 (목록용)"""

    id: str
    title: str
    last_message_at: datetime | None = None
    message_count: int = 0


class ConversationListResponse(BaseModel):
    """대화 목록 응답"""

    conversations: list[ConversationSummary]


class ConversationDetailResponse(BaseModel):
    """대화 상세 응답 (메시지 포함)"""

    id: str
    title: str
    messages: list[MessageResponse]
    created_at: datetime
    updated_at: datetime
    agent_state: dict | None = None
    summary: str | None = None
    total_tokens: int = 0
