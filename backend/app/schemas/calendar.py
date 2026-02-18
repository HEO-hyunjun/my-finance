from __future__ import annotations

from datetime import date

from pydantic import BaseModel


class CalendarEventType:
    """캘린더 이벤트 유형 상수"""
    FIXED_EXPENSE = "fixed_expense"
    INSTALLMENT = "installment"
    MATURITY = "maturity"
    EXPENSE = "expense"
    INCOME = "income"


EVENT_COLOR_MAP = {
    CalendarEventType.FIXED_EXPENSE: "#6B7280",  # Gray
    CalendarEventType.INSTALLMENT: "#3B82F6",    # Blue
    CalendarEventType.MATURITY: "#10B981",        # Green
    CalendarEventType.EXPENSE: "#EF4444",          # Red
    CalendarEventType.INCOME: "#F59E0B",           # Amber
}


class CalendarEvent(BaseModel):
    """캘린더 이벤트"""
    date: date
    type: str  # CalendarEventType 값
    title: str
    amount: float
    color: str  # HEX 색상 코드
    description: str | None = None
    source_asset_name: str | None = None


class DaySummary(BaseModel):
    """일자별 요약"""
    date: date
    total_amount: float
    total_expense: float = 0.0
    total_income: float = 0.0
    event_count: int
    event_types: list[str]


class MonthSummary(BaseModel):
    """월 요약"""
    year: int
    month: int
    total_scheduled_amount: float
    total_expense_amount: float
    total_income_amount: float = 0.0
    event_count: int
    maturity_count: int


class CalendarEventsResponse(BaseModel):
    """캘린더 이벤트 응답"""
    events: list[CalendarEvent]
    day_summaries: list[DaySummary]
    month_summary: MonthSummary
