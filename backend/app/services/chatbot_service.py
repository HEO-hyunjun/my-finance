"""챗봇 서비스.

LangGraph 기반 AI 재무 상담 챗봇. 신규 스키마(Account, Entry) 기반.
"""

import logging
import re
import uuid
from collections import Counter
from collections.abc import AsyncGenerator
from datetime import datetime, timezone

from litellm import acompletion
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.core.config import settings
from app.core.tz import today as get_today
from app.models.conversation import Conversation, Message
from app.schemas.chatbot import (
    ChatAgentEvent,
    ChatDoneEvent,
    ChatErrorEvent,
    ChatGeneratingEvent,
    ChatTokenEvent,
    ChatToolEvent,
    ConversationDetailResponse,
    ConversationListResponse,
    ConversationSummary,
    MessageResponse,
)
from app.services.budget_analysis_service import get_budget_analysis
from app.services.budget_v2_service import get_budget_overview
from app.services.market_service import MarketService
from app.services.portfolio_v2_service import get_total_assets

logger = logging.getLogger(__name__)


# =====================================================
# Context Builder
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
    today_ = get_today()

    # 자산 현황 (portfolio_v2_service)
    try:
        assets = await get_total_assets(db, user_id)
        account_lines = []
        for acc in assets["accounts"]:
            account_lines.append(f"- {acc['name']} ({acc['account_type']}): ₩{acc['total_value_krw']:,.0f}")
        parts.append(f"### 자산 현황\n- **총 자산**: ₩{assets['total_krw']:,.0f}\n" + "\n".join(account_lines))
    except Exception:
        parts.append("### 자산 현황\n- 데이터를 불러올 수 없습니다.")

    # 예산 현황 (budget_v2_service)
    try:
        overview = await get_budget_overview(db, user_id, today_)
        parts.append(
            f"### 예산 현황\n"
            f"- 기간: {overview['period_start']} ~ {overview['period_end']}\n"
            f"- 총 수입: ₩{overview['total_income']:,.0f}\n"
            f"- 고정 지출: ₩{overview['total_fixed_expense']:,.0f}\n"
            f"- 가용 예산: ₩{overview['available_budget']:,.0f}\n"
            f"- 미배분: ₩{overview['unallocated']:,.0f}"
        )
    except Exception:
        parts.append("### 예산 현황\n- 데이터를 불러올 수 없습니다.")

    # 예산 분석 (budget_analysis_service — 기존 유지)
    try:
        analysis = await get_budget_analysis(db, user_id)
        parts.append(
            f"### 예산 분석\n"
            f"- 오늘 가용 예산: ₩{analysis.daily_budget.daily_available:,.0f}\n"
            f"- 오늘 지출: ₩{analysis.daily_budget.today_spent:,.0f}\n"
            f"- 남은 일수: {analysis.daily_budget.remaining_days}일\n"
            f"- 주간 지출: ₩{analysis.weekly_analysis.week_spent:,.0f} "
            f"(주간 예산 대비 {analysis.weekly_analysis.usage_rate:.1f}%)"
        )
        if analysis.alerts:
            parts.append("- 경고: " + "; ".join(analysis.alerts[:3]))
    except Exception:
        pass

    try:
        exchange_rate = await market.get_exchange_rate()
        parts.append(
            f"### 시장 정보\n- USD/KRW 환율: \u20a9{exchange_rate.rate:,.2f} (변동: {exchange_rate.change:+.2f})"
        )
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
        agent_state=conv.agent_state,
        summary=conv.summary,
        total_tokens=conv.total_tokens or 0,
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
    """SSE 스트리밍 채팅 응답 생성기 (LangGraph 기반)"""
    from app.services.agents.graph import AgentGraph

    # 1. 대화 세션 조회 또는 생성
    conv: Conversation
    if conversation_id:
        stmt = (
            select(Conversation)
            .options(selectinload(Conversation.messages))
            .where(
                Conversation.id == uuid.UUID(conversation_id),
                Conversation.user_id == user_id,
            )
        )
        result = await db.execute(stmt)
        found = result.scalar_one_or_none()
        if not found:
            yield _sse_event(ChatErrorEvent(message="대화를 찾을 수 없습니다."))
            return
        conv = found
    else:
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

    # messages 관계를 명시적으로 로드 (async lazy loading 방지)
    await db.refresh(conv, ["messages"])

    # 3. 대화 히스토리 구성
    history = _build_history(conv.messages, settings.CHATBOT_MAX_HISTORY, summary=conv.summary)

    # 4. LangGraph 에이전트 그래프 실행
    graph = AgentGraph()
    full_response = ""
    graph_state: dict = {}

    async for event in graph.run_stream(
        db=db,
        user_id=user_id,
        query=message,
        conversation_id=str(conv.id),
        history=history,
        market=market,
    ):
        if event["type"] == "agent":
            yield _sse_event(ChatAgentEvent(name=event["name"], status=event["status"]))

        elif event["type"] == "tool":
            yield _sse_event(
                ChatToolEvent(
                    agent=event["agent"],
                    name=event["name"],
                    status=event["status"],
                )
            )

        elif event["type"] == "generating":
            yield _sse_event(ChatGeneratingEvent())

        elif event["type"] == "token":
            full_response += event["content"]
            yield _sse_event(ChatTokenEvent(content=event["content"]))

        elif event["type"] == "error":
            yield _sse_event(ChatErrorEvent(message=event["message"]))
            return

        elif event["type"] == "done":
            graph_state = event.get("state", {})

    # 5. AI 응답 메시지 저장
    assistant_msg = Message(
        conversation_id=conv.id,
        role="assistant",
        content=full_response,
        model=settings.chatbot_model,
    )
    db.add(assistant_msg)

    # 6. 체크포인트 상태를 DB에도 반영
    conv.agent_state = graph_state
    conv.total_tokens = (conv.total_tokens or 0) + (assistant_msg.token_count or 0)

    # 6.1. 컨텍스트 스냅샷 저장 (사용자 관심 패턴 추적)
    await save_context_snapshot(db, conv, list(conv.messages) + [assistant_msg])

    # 대화가 길어지면 자동 요약 (10턴 이상)
    if len(conv.messages) >= 20 and not conv.summary:
        conv.summary = await _generate_conversation_summary(conv.messages[:16])

    # 7. 대화 updated_at 갱신
    conv.updated_at = datetime.now(timezone.utc)
    await db.commit()

    # 8. 완료 이벤트
    yield _sse_event(
        ChatDoneEvent(
            conversation_id=str(conv.id),
            message_id=str(assistant_msg.id),
        )
    )


async def _generate_conversation_summary(messages: list[Message]) -> str | None:
    """긴 대화의 이전 메시지를 요약"""
    try:
        msg_text = "\n".join(f"{m.role}: {m.content[:200]}" for m in messages)
        response = await acompletion(
            model=settings.chatbot_model,
            messages=[
                {
                    "role": "system",
                    "content": "다음 대화를 3-4문장으로 요약하세요. 핵심 주제와 결론을 포함하세요.",
                },
                {"role": "user", "content": msg_text},
            ],
            max_tokens=256,
            temperature=0.3,
        )
        return response.choices[0].message.content
    except Exception:
        return None


def _build_history(
    messages: list[Message],
    max_turns: int,
    summary: str | None = None,
) -> list[dict[str, str]]:
    """대화 히스토리를 LLM 메시지 포맷으로 변환 (최근 N턴)"""
    history: list[dict[str, str]] = []
    if summary:
        history.append({"role": "system", "content": f"이전 대화 요약: {summary}"})
    recent = messages[-(max_turns * 2) :]
    history.extend([{"role": m.role, "content": m.content} for m in recent])
    return history


def _sse_event(
    event: ChatTokenEvent | ChatDoneEvent | ChatErrorEvent | ChatAgentEvent | ChatToolEvent | ChatGeneratingEvent,
) -> str:
    """EventSourceResponse가 data: 접두사를 자동 추가하므로 JSON만 반환"""
    return event.model_dump_json()


# =====================================================
# Context Snapshot — 사용자 패턴 추적 (P4)
# =====================================================

# 금융 관련 키워드 패턴 (종목명, 지수 등)
_FINANCIAL_PATTERNS = re.compile(
    r"(삼성전자|SK하이닉스|네이버|카카오|현대차|LG에너지솔루션|셀트리온|POSCO|기아"
    r"|AAPL|TSLA|NVDA|MSFT|AMZN|GOOGL|META|NFLX|S&P\s?500|나스닥|코스피|코스닥"
    r"|비트코인|이더리움|금|은|환율|달러|엔화|유로"
    r"|예금|적금|펀드|ETF|채권|부동산|연금"
    r"|배당|PER|PBR|ROE|EPS|시총)",
    re.IGNORECASE,
)


def _extract_topics(messages: list[Message]) -> list[str]:
    """메시지에서 금융 관련 토픽 추출"""
    all_topics: list[str] = []
    for m in messages:
        if m.role == "user":
            found = _FINANCIAL_PATTERNS.findall(m.content)
            all_topics.extend(found)
    return all_topics


async def save_context_snapshot(
    db: AsyncSession,
    conv: Conversation,
    messages: list[Message],
) -> None:
    """대화 완료 시 context_snapshot에 사용자 관심 패턴 저장"""
    topics = _extract_topics(messages)
    if not topics:
        return

    topic_counts = Counter(t.lower() for t in topics)
    snapshot = {
        "topics": dict(topic_counts.most_common(10)),
        "message_count": len(messages),
        "timestamp": datetime.now(timezone.utc).isoformat(),
    }
    conv.context_snapshot = snapshot


async def load_user_patterns(
    db: AsyncSession,
    user_id: uuid.UUID,
) -> str | None:
    """최근 대화 스냅샷에서 사용자 관심사를 추출하여 시스템 프롬프트용 문자열 반환"""
    stmt = (
        select(Conversation)
        .where(
            Conversation.user_id == user_id,
            Conversation.context_snapshot.isnot(None),
        )
        .order_by(Conversation.updated_at.desc())
        .limit(5)
    )
    result = await db.execute(stmt)
    conversations = result.scalars().all()

    if not conversations:
        return None

    # 모든 스냅샷의 토픽 집계
    aggregated: Counter[str] = Counter()
    for conv in conversations:
        snapshot = conv.context_snapshot
        if snapshot and "topics" in snapshot:
            for topic, count in snapshot["topics"].items():
                aggregated[topic] += count

    if not aggregated:
        return None

    top_topics = aggregated.most_common(8)
    lines = [f"- {topic} (관심도: {count}회)" for topic, count in top_topics]
    return "### 사용자 관심 분야\n" + "\n".join(lines)
