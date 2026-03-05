from celery import Celery
from celery.schedules import crontab
from app.core.config import settings

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
    ],
)

celery_app.conf.update(
    timezone="Asia/Seoul",
    enable_utc=True,
    task_serializer="json",
    accept_content=["json"],
    result_serializer="json",
    task_track_started=True,
    worker_hijack_root_logger=False,
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
    "collect-news-batch": {
        "task": "app.tasks.news_tasks.collect_news_batch",
        "schedule": crontab(hour="7,19", minute=0),  # 하루 2회 (07:00, 19:00)
    },
    "process-and-cluster-news": {
        "task": "app.tasks.news_tasks.process_and_cluster_news",
        "schedule": crontab(hour="*/6", minute=30),  # 6시간마다
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
}
