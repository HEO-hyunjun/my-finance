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
    "deduct-fixed-expenses-daily": {
        "task": "app.tasks.budget_tasks.deduct_fixed_expenses",
        "schedule": crontab(hour=0, minute=5),  # 매일 00:05
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
}
