import logging

from celery import Celery
from celery.schedules import crontab
from celery.signals import after_setup_logger
from app.core.config import settings


@after_setup_logger.connect
def setup_app_loggers(logger, loglevel, **kwargs):
    """Celery worker 시작 후 앱 로거에 핸들러를 설정.

    Celery는 자체 로거만 설정하고 앱 로거(app.tasks.*)는 건드리지 않아
    logger.info()가 출력되지 않는 문제를 해결한다.
    """
    app_logger = logging.getLogger("app")
    app_logger.setLevel(loglevel)
    if not app_logger.handlers:
        handler = logging.StreamHandler()
        handler.setLevel(loglevel)
        formatter = logging.Formatter(
            "[%(asctime)s: %(levelname)s/%(processName)s] %(message)s"
        )
        handler.setFormatter(formatter)
        app_logger.addHandler(handler)

celery_app = Celery(
    "myfinance",
    broker=settings.REDIS_URL,
    backend=settings.REDIS_URL,
    include=[
        "app.tasks.budget_tasks",
        "app.tasks.snapshot_tasks",
        "app.tasks.news_tasks",
        "app.tasks.market_tasks",
        "app.tasks.insight_tasks",
        "app.tasks.interest_tasks",
        "app.tasks.auto_transfer_tasks",
        "app.tasks.income_tasks",
        "app.tasks.compensation_tasks",
    ],
)

celery_app.conf.update(
    timezone="Asia/Seoul",
    enable_utc=True,
    task_serializer="json",
    accept_content=["json"],
    result_serializer="json",
    task_track_started=True,
)

# Celery Beat schedule
celery_app.conf.beat_schedule = {
    "initialize-period-fixed-expenses-daily": {
        "task": "app.tasks.budget_tasks.initialize_period_fixed_expenses",
        "schedule": crontab(hour=0, minute=1),  # 매일 00:01
    },
    "deduct-installments-daily": {
        "task": "app.tasks.budget_tasks.deduct_installments",
        "schedule": crontab(hour=0, minute=10),  # 매일 00:10
    },
    "take-asset-snapshot-daily": {
        "task": "app.tasks.snapshot_tasks.take_daily_snapshot",
        "schedule": crontab(hour=23, minute=55),  # 매일 23:55
    },
    "collect-and-process-news": {
        "task": "app.tasks.news_tasks.collect_and_process_news",
        "schedule": crontab(hour="8,17", minute=50),  # 하루 2회: 수집 → LLM 처리 → 클러스터링 통합
    },
    # 시세 캐시 워밍: 한국장 마감(15:35), 미국장 마감(06:05 KST), 자정
    "warm-market-cache-kr-close": {
        "task": "app.tasks.market_tasks.warm_market_cache",
        "schedule": crontab(hour=15, minute=35),
    },
    "warm-market-cache-us-close": {
        "task": "app.tasks.market_tasks.warm_market_cache",
        "schedule": crontab(hour=6, minute=5),
    },
    "warm-market-cache-midnight": {
        "task": "app.tasks.market_tasks.warm_market_cache",
        "schedule": crontab(hour=0, minute=0),
    },
    "generate-daily-insights": {
        "task": "app.tasks.insight_tasks.generate_all_user_insights",
        "schedule": crontab(hour=6, minute=0),  # 매일 06:00
    },
    "record-parking-interest-daily": {
        "task": "app.tasks.interest_tasks.record_daily_parking_interest",
        "schedule": crontab(hour=0, minute=5),  # 매일 00:05
    },
    "record-deposit-interest-monthly": {
        "task": "app.tasks.interest_tasks.record_monthly_deposit_interest",
        "schedule": crontab(hour=0, minute=15, day_of_month=1),  # 매월 1일 00:15
    },
    "execute-auto-transfers-daily": {
        "task": "app.tasks.auto_transfer_tasks.execute_auto_transfers",
        "schedule": crontab(hour=9, minute=0),  # 매일 09:00
    },
    "generate-recurring-incomes-daily": {
        "task": "app.tasks.income_tasks.generate_recurring_incomes",
        "schedule": crontab(hour=0, minute=3),  # 매일 00:03
    },
    "cleanup-old-news-weekly": {
        "task": "app.tasks.news_tasks.cleanup_old_news",
        "schedule": crontab(hour=3, minute=0, day_of_week=0),  # 매주 일요일 03:00
    },
}
