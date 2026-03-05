"""앱 전역 타임존 유틸리티.

모든 날짜/시간 계산은 이 모듈을 통해 수행하여 일관성을 유지한다.
환경변수 TIMEZONE(기본값: Asia/Seoul)으로 제어.

사용법:
    from app.core.tz import now, today, APP_TZ
"""

from datetime import date, datetime, timezone
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
