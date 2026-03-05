import json
import logging
import uuid

from litellm import acompletion
from sqlalchemy import select, delete
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.core.tz import today
from app.models.insight import AIInsightRecord
from app.services.asset_service import get_asset_summary
from app.services.budget_analysis_service import get_budget_analysis
from app.services.budget_service import get_budget_summary
from app.services.market_service import MarketService
from app.services.transaction_service import get_transactions

logger = logging.getLogger(__name__)


async def get_ai_insights(
    db: AsyncSession,
    user_id: uuid.UUID,
) -> list[dict]:
    """DB에서 오늘 날짜의 AI 인사이트를 조회. 없으면 빈 리스트 반환."""
    today_ = today()
    result = await db.execute(
        select(AIInsightRecord)
        .where(
            AIInsightRecord.user_id == user_id,
            AIInsightRecord.generated_date == today_,
        )
        .order_by(AIInsightRecord.created_at)
    )
    records = result.scalars().all()
    return [
        {
            "type": r.type,
            "title": r.title,
            "description": r.description,
            "severity": r.severity,
            "generated_at": str(r.generated_date),
        }
        for r in records
    ]


async def generate_daily_insights(
    db: AsyncSession,
    user_id: uuid.UUID,
    market: MarketService,
    salary_day: int = 1,
) -> list[dict]:
    """LLM을 호출하여 인사이트를 생성하고 DB에 저장. 이미 있으면 재생성."""
    today_ = today()

    # 기존 데이터 삭제 (upsert 패턴)
    await db.execute(
        delete(AIInsightRecord).where(
            AIInsightRecord.user_id == user_id,
            AIInsightRecord.generated_date == today_,
        )
    )

    # 재무 데이터 수집
    context_parts: list[str] = []

    try:
        asset_summary = await get_asset_summary(db, user_id, market)
        context_parts.append(
            f"총 자산: ₩{asset_summary.total_value_krw:,.0f}, "
            f"수익률: {asset_summary.total_profit_loss_rate:+.2f}%, "
            f"자산 분포: {json.dumps(asset_summary.breakdown, ensure_ascii=False)}"
        )
    except Exception:
        pass

    try:
        budget = await get_budget_summary(db, user_id, salary_day=salary_day)
        context_parts.append(
            f"예산: ₩{budget.total_budget:,.0f}, "
            f"지출: ₩{budget.total_spent:,.0f}, "
            f"사용률: {budget.total_usage_rate:.1f}%"
        )
    except Exception:
        pass

    try:
        analysis = await get_budget_analysis(db, user_id, salary_day=salary_day)
        context_parts.append(
            f"일일 가용: ₩{analysis.daily_budget.daily_available:,.0f}, "
            f"오늘 지출: ₩{analysis.daily_budget.today_spent:,.0f}, "
            f"남은 일수: {analysis.daily_budget.remaining_days}일"
        )
        if analysis.alerts:
            context_parts.append(f"경고: {'; '.join(analysis.alerts[:3])}")
    except Exception:
        pass

    try:
        recent_tx = await get_transactions(db, user_id, page=1, per_page=10)
        if recent_tx.data:
            tx_summary = ", ".join(
                f"{tx.asset_name}({tx.type})" for tx in recent_tx.data[:5]
            )
            context_parts.append(f"최근 거래: {tx_summary}")
    except Exception:
        pass

    if not context_parts:
        return []

    # LLM 호출로 인사이트 생성
    prompt = f"""사용자의 재무 데이터를 분석하여 3-5개의 실용적 인사이트를 생성하세요.

## 재무 현황
{chr(10).join(context_parts)}

## 인사이트 유형
- spending: 지출 패턴 분석 및 절약 팁
- budget: 예산 관리 조언
- investment: 포트폴리오/투자 제안
- saving: 저축 목표 관련
- alert: 주의가 필요한 사항

아래 JSON 배열로만 응답하세요:
[
  {{
    "type": "spending | budget | investment | saving | alert",
    "title": "인사이트 제목 (15자 이내)",
    "description": "상세 설명 (50자 이내)",
    "severity": "info | warning | success"
  }}
]"""

    try:
        response = await acompletion(
            model=settings.insight_model,
            messages=[{"role": "user", "content": prompt}],
            max_tokens=settings.INSIGHT_MAX_TOKENS,
            temperature=settings.INSIGHT_TEMPERATURE,
        )

        content = response.choices[0].message.content.strip()
        if "```json" in content:
            content = content.split("```json")[1].split("```")[0].strip()
        elif "```" in content:
            content = content.split("```")[1].split("```")[0].strip()

        insights = json.loads(content)

        # 유효성 검사 및 DB 저장
        valid_types = {"spending", "budget", "investment", "saving", "alert"}
        valid_severities = {"info", "warning", "success"}
        validated = []
        for item in insights:
            if (
                isinstance(item, dict)
                and item.get("type") in valid_types
                and item.get("severity") in valid_severities
                and item.get("title")
                and item.get("description")
            ):
                record = AIInsightRecord(
                    user_id=user_id,
                    type=item["type"],
                    title=item["title"][:100],
                    description=item["description"][:500],
                    severity=item["severity"],
                    generated_date=today_,
                )
                db.add(record)
                validated.append(item)

        await db.commit()
        return validated
    except Exception as e:
        logger.warning(f"AI insight generation failed: {e}")
        await db.rollback()
        return []
