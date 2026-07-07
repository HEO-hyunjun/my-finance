"""앱 전역 타임존 유틸리티.

모든 날짜/시간 계산은 이 모듈을 통해 수행하여 일관성을 유지한다.
환경변수 TIMEZONE(기본값: Asia/Seoul)으로 제어.

사용법:
    from app.core.tz import now, today, APP_TZ
"""

from datetime import date, datetime, time, timedelta, timezone
from zoneinfo import ZoneInfo

from app.core.config import settings

APP_TZ = ZoneInfo(settings.TIMEZONE)


def now() -> datetime:
    """앱 타임존 기준 현재 시각 (timezone-aware)"""
    return datetime.now(APP_TZ)


def today() -> date:
    """앱 타임존 기준 오늘 날짜"""
    return now().date()


def to_utc(dt: datetime) -> datetime:
    """앱 타임존 datetime을 UTC로 변환"""
    return dt.astimezone(timezone.utc)


def kst_day_utc_range(d: date) -> tuple[datetime, datetime]:
    """앱 타임존 기준 하루(00:00~다음날 00:00)의 UTC 범위를 반환."""
    start = datetime.combine(d, time.min, tzinfo=APP_TZ).astimezone(timezone.utc)
    end = datetime.combine(d + timedelta(days=1), time.min, tzinfo=APP_TZ).astimezone(timezone.utc)
    return start, end


def kst_month_utc_range(d: date) -> tuple[datetime, datetime]:
    """앱 타임존 기준 이번 달(1일 00:00~다음달 1일 00:00)의 UTC 범위를 반환."""
    month_start = d.replace(day=1)
    if month_start.month == 12:
        next_month = date(month_start.year + 1, 1, 1)
    else:
        next_month = date(month_start.year, month_start.month + 1, 1)
    start = datetime.combine(month_start, time.min, tzinfo=APP_TZ).astimezone(timezone.utc)
    end = datetime.combine(next_month, time.min, tzinfo=APP_TZ).astimezone(timezone.utc)
    return start, end


def kst_noon_utc(d: date) -> datetime:
    """앱 타임존 기준 해당 날짜 정오의 UTC datetime을 반환."""
    return datetime.combine(d, time(12, 0), tzinfo=APP_TZ).astimezone(timezone.utc)
