"""가계부 분석 서브에이전트.

예산, 지출, 수입, 고정비, 할부금을 분석합니다.
신규 스키마(Entry, Category) 기반.
"""

import json
import uuid
from typing import Any

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.tz import today as get_today
from app.models.entry import Entry, EntryType
from app.models.recurring_schedule import ScheduleType
from app.services.agents.sub_agent import SubAgent
from app.services.budget_v2_service import get_budget_overview, get_category_budgets
from app.services.market_service import MarketService
from app.services.schedule_service import get_schedules


class BudgetAgent(SubAgent):
    name = "budget"
    display_name = "가계부 분석"
    description = "예산 현황, 지출 분석, 수입 내역, 고정비, 할부금 분석"
    system_prompt = """당신은 가계부/예산 분석 전문가입니다.

## 역할
- 사용자의 예산 현황과 지출 패턴을 분석합니다.
- 수입/지출 내역을 조회하고 트렌드를 파악합니다.
- 예산 초과 위험을 경고하고 절약 방안을 제안합니다.
- 고정비와 할부금 관리 상태를 점검합니다.

## 분석 방법
- 카테고리별 예산 사용률을 분석합니다.
- 일별/주간 지출 패턴을 파악합니다.
- 고정비 대비 변동비 비율을 계산합니다.
- 할부금 잔여 금액과 완료 예정일을 추적합니다.

## 응답 규칙
- 금액은 ₩ 기호와 천 단위 구분자 사용
- 카테고리별 사용률을 명확히 표시
- 경고가 필요한 카테고리를 강조
- 구체적인 절약/관리 방안 제시"""

    def get_tool_definitions(self) -> list[dict]:
        return [
            {
                "type": "function",
                "function": {
                    "name": "get_budget_status",
                    "description": "이번 달 예산 현황 (총 예산, 지출, 잔여액, 카테고리별 사용률)",
                    "parameters": {"type": "object", "properties": {}},
                },
            },
            {
                "type": "function",
                "function": {
                    "name": "get_budget_analysis",
                    "description": "예산 분석 (일별 가용액, 주간 분석, 카테고리 사용률, 이월 예측, 경고)",
                    "parameters": {"type": "object", "properties": {}},
                },
            },
            {
                "type": "function",
                "function": {
                    "name": "get_expense_list",
                    "description": "지출 내역 조회 (날짜 필터 가능)",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "start_date": {
                                "type": "string",
                                "description": "조회 시작일 (YYYY-MM-DD)",
                            },
                            "end_date": {
                                "type": "string",
                                "description": "조회 종료일 (YYYY-MM-DD)",
                            },
                            "per_page": {
                                "type": "integer",
                                "description": "조회 건수 (기본: 20, 최대: 50)",
                            },
                        },
                    },
                },
            },
            {
                "type": "function",
                "function": {
                    "name": "get_income_list",
                    "description": "수입 내역 조회 (급여, 부업, 투자소득 등)",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "start_date": {
                                "type": "string",
                                "description": "조회 시작일 (YYYY-MM-DD)",
                            },
                            "end_date": {
                                "type": "string",
                                "description": "조회 종료일 (YYYY-MM-DD)",
                            },
                            "income_type": {
                                "type": "string",
                                "description": "수입 유형 필터 (salary, side, investment, other)",
                            },
                        },
                    },
                },
            },
            {
                "type": "function",
                "function": {
                    "name": "get_fixed_expenses",
                    "description": "고정비 목록 조회 (매월 정기 지출)",
                    "parameters": {"type": "object", "properties": {}},
                },
            },
            {
                "type": "function",
                "function": {
                    "name": "get_installments",
                    "description": "할부금 목록 조회 (진도율, 잔여 금액 포함)",
                    "parameters": {"type": "object", "properties": {}},
                },
            },
        ]

    async def execute_tool(
        self,
        tool_name: str,
        args: dict,
        db: AsyncSession,
        user_id: uuid.UUID,
        market: MarketService,
    ) -> Any:
        if tool_name == "get_budget_status":
            today_ = get_today()
            overview = await get_budget_overview(db, user_id, today_)
            categories = await get_category_budgets(db, user_id, today_)
            # Decimal → float for JSON serialization
            for k, v in overview.items():
                if hasattr(v, "as_tuple"):
                    overview[k] = float(v)
            for cat in categories:
                for k, v in cat.items():
                    if hasattr(v, "as_tuple"):
                        cat[k] = float(v)
            return {
                "overview": overview,
                "categories": categories,
            }

        if tool_name == "get_budget_analysis":
            from app.services.budget_analysis_service import get_budget_analysis

            analysis = await get_budget_analysis(db, user_id)
            return json.loads(analysis.model_dump_json())

        if tool_name == "get_expense_list":
            per_page = min(args.get("per_page", 20), 50)
            stmt = (
                select(Entry)
                .where(Entry.user_id == user_id, Entry.type == EntryType.EXPENSE)
                .order_by(Entry.transacted_at.desc())
            )
            if args.get("start_date"):
                stmt = stmt.where(Entry.transacted_at >= args["start_date"])
            if args.get("end_date"):
                stmt = stmt.where(Entry.transacted_at <= args["end_date"])
            stmt = stmt.limit(per_page)
            result = await db.execute(stmt)
            entries = result.scalars().all()
            return [
                {
                    "id": str(e.id),
                    "amount": float(e.amount),
                    "currency": e.currency,
                    "memo": e.memo,
                    "category_id": str(e.category_id) if e.category_id else None,
                    "transacted_at": e.transacted_at.isoformat(),
                }
                for e in entries
            ]

        if tool_name == "get_income_list":
            stmt = (
                select(Entry)
                .where(Entry.user_id == user_id, Entry.type == EntryType.INCOME)
                .order_by(Entry.transacted_at.desc())
            )
            if args.get("start_date"):
                stmt = stmt.where(Entry.transacted_at >= args["start_date"])
            if args.get("end_date"):
                stmt = stmt.where(Entry.transacted_at <= args["end_date"])
            stmt = stmt.limit(20)
            result = await db.execute(stmt)
            entries = result.scalars().all()
            return [
                {
                    "id": str(e.id),
                    "amount": float(e.amount),
                    "currency": e.currency,
                    "memo": e.memo,
                    "category_id": str(e.category_id) if e.category_id else None,
                    "transacted_at": e.transacted_at.isoformat(),
                }
                for e in entries
            ]

        if tool_name == "get_fixed_expenses":
            schedules = await get_schedules(db, user_id)
            fixed = [s for s in schedules if s.type == ScheduleType.EXPENSE and s.is_active]
            return [
                {
                    "id": str(s.id),
                    "name": s.name,
                    "amount": float(s.amount),
                    "currency": s.currency,
                    "schedule_day": s.schedule_day,
                    "is_active": s.is_active,
                }
                for s in fixed
            ]

        if tool_name == "get_installments":
            schedules = await get_schedules(db, user_id)
            installments = [s for s in schedules if s.total_count is not None and s.is_active]
            return [
                {
                    "id": str(s.id),
                    "name": s.name,
                    "amount": float(s.amount),
                    "currency": s.currency,
                    "schedule_day": s.schedule_day,
                    "total_count": s.total_count,
                    "executed_count": s.executed_count,
                    "remaining_count": (s.total_count - s.executed_count) if s.total_count else None,
                    "remaining_amount": float(s.amount * (s.total_count - s.executed_count)) if s.total_count else None,
                }
                for s in installments
            ]

        return {"error": f"Unknown tool: {tool_name}"}
