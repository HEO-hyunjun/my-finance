"""앱 시작 시 누락된 일일 태스크를 보상 실행하는 모듈.

FastAPI lifespan에서 호출되어, 다운타임 중 놓친 태스크를 복구한다.
DB 기반으로 이번 달 누락 건을 체크하므로, 배포 시점과 무관하게 안전하게 동작.
"""

import logging

from app.core.celery_app import celery_app

logger = logging.getLogger(__name__)


def run_missed_tasks():
    """누락 가능성이 있는 일일 태스크를 지연 실행으로 큐에 전송."""
    tasks = [
        ("app.tasks.schedule_tasks.compensate_missed_schedules", 10),
        ("app.tasks.interest_tasks.record_daily_parking_interest", 15),
        ("app.tasks.market_tasks.warm_market_cache", 20),
        ("app.tasks.snapshot_tasks.take_daily_snapshot", 25),
    ]
    for task_name, countdown in tasks:
        try:
            celery_app.send_task(task_name, countdown=countdown)
            logger.info(f"Compensation task queued: {task_name} (in {countdown}s)")
        except Exception as e:
            logger.warning(f"Failed to queue compensation task {task_name}: {e}")
