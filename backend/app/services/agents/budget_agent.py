"""가계부 분석 서브에이전트.

예산, 지출, 수입, 고정비, 할부금을 분석합니다.
"""

import json
import uuid
from typing import Any

from sqlalchemy.ext.asyncio import AsyncSession

from app.services.agents.sub_agent import SubAgent
from app.services.market_service import MarketService


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
            from sqlalchemy import select as sa_select

            from app.models.user import User as UserModel
            from app.services.budget_service import get_budget_summary

            stmt = sa_select(UserModel.salary_day).where(UserModel.id == user_id)
            row = await db.execute(stmt)
            salary_day = row.scalar_one_or_none() or 1

            summary = await get_budget_summary(db, user_id, salary_day=salary_day)
            return json.loads(summary.model_dump_json())

        if tool_name == "get_budget_analysis":
            from app.services.budget_analysis_service import get_budget_analysis

            analysis = await get_budget_analysis(db, user_id)
            return json.loads(analysis.model_dump_json())

        if tool_name == "get_expense_list":
            from datetime import date as date_type

            from app.services.budget_service import get_expenses

            start = (
                date_type.fromisoformat(args["start_date"])
                if args.get("start_date")
                else None
            )
            end = (
                date_type.fromisoformat(args["end_date"])
                if args.get("end_date")
                else None
            )

            expense_resp = await get_expenses(
                db,
                user_id,
                start_date=start,
                end_date=end,
                per_page=min(args.get("per_page", 20), 50),
            )
            return json.loads(expense_resp.model_dump_json())

        if tool_name == "get_income_list":
            from datetime import date as date_type

            from app.services.income_service import get_incomes

            start = (
                date_type.fromisoformat(args["start_date"])
                if args.get("start_date")
                else None
            )
            end = (
                date_type.fromisoformat(args["end_date"])
                if args.get("end_date")
                else None
            )

            income_resp = await get_incomes(
                db,
                user_id,
                income_type=args.get("income_type"),
                start_date=start,
                end_date=end,
                per_page=min(args.get("per_page", 20), 50),
            )
            return json.loads(income_resp.model_dump_json())

        if tool_name == "get_fixed_expenses":
            from app.services.budget_service import get_fixed_expenses

            fixed_resp = await get_fixed_expenses(db, user_id)
            return [json.loads(f.model_dump_json()) for f in fixed_resp]

        if tool_name == "get_installments":
            from app.services.budget_service import get_installments

            inst_resp = await get_installments(db, user_id)
            return [json.loads(i.model_dump_json()) for i in inst_resp]

        return {"error": f"Unknown tool: {tool_name}"}
