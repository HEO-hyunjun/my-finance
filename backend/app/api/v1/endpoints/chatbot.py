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
        ),
        headers={
            "Cache-Control": "no-cache",
            "X-Accel-Buffering": "no",
        },
        ping=15,
    )


@router.get("/conversations", response_model=ConversationListResponse)
async def list_conversations(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """대화 목록 조회"""
    return await get_conversations(db, current_user.id)


@router.get(
    "/conversations/{conversation_id}",
    response_model=ConversationDetailResponse,
)
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


@router.get("/agents")
async def get_agents(current_user: User = Depends(get_current_user)):
    """사용 가능한 도구 목록 조회"""
    from app.services.agents.graph import AgentGraph
    graph = AgentGraph()
    return {"agents": graph.get_agent_info()}


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
