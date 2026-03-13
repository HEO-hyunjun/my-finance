"""앱 시작 시 누락된 일일 태스크를 보상 실행하는 모듈.

FastAPI lifespan에서 호출되어, 다운타임 중 놓친 태스크를 복구한다.
각 태스크는 내부에 중복 방지 로직이 있으므로 안전하게 재실행 가능.
"""
import logging

from app.core.celery_app import celery_app

logger = logging.getLogger(__name__)

# (태스크 이름, countdown 초) - 워커 준비 대기를 위해 지연 실행
DAILY_TASKS = [
    ("app.tasks.budget_tasks.initialize_period_fixed_expenses", 5),
    ("app.tasks.budget_tasks.deduct_installments", 8),
    ("app.tasks.income_tasks.generate_recurring_incomes", 10),
    ("app.tasks.interest_tasks.record_daily_parking_interest", 12),
    ("app.tasks.auto_transfer_tasks.execute_auto_transfers", 15),
    ("app.tasks.market_tasks.warm_market_cache", 20),
]


def run_missed_tasks():
    """누락 가능성이 있는 일일 태스크를 지연 실행으로 큐에 전송."""
    for task_name, countdown in DAILY_TASKS:
        try:
            celery_app.send_task(task_name, countdown=countdown)
            logger.info(f"Compensation task queued: {task_name} (in {countdown}s)")
        except Exception as e:
            logger.warning(f"Failed to queue compensation task {task_name}: {e}")
