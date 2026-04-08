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
        "app.tasks.schedule_tasks",
        "app.tasks.interest_tasks",
        "app.tasks.snapshot_tasks",
        "app.tasks.market_tasks",
        "app.tasks.insight_tasks",
        "app.tasks.price_tasks",
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
    "execute-daily-schedules": {
        "task": "app.tasks.schedule_tasks.execute_daily_schedules",
        "schedule": crontab(hour=0, minute=1),
    },
    "record-parking-interest-daily": {
        "task": "app.tasks.interest_tasks.record_daily_parking_interest",
        "schedule": crontab(hour=0, minute=5),
    },
    "record-deposit-interest-monthly": {
        "task": "app.tasks.interest_tasks.record_monthly_deposit_interest",
        "schedule": crontab(hour=0, minute=15, day_of_month=1),
    },
    "take-asset-snapshot-daily": {
        "task": "app.tasks.snapshot_tasks.take_daily_snapshot",
        "schedule": crontab(hour=23, minute=55),
    },
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
        "schedule": crontab(hour=6, minute=0),
    },
    "collect-daily-prices": {
        "task": "app.tasks.price_tasks.collect_daily_prices",
        "schedule": crontab(hour=16, minute=0),
    },
}
