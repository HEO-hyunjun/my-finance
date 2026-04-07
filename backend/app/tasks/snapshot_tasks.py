"""일일 자산 스냅샷 태스크.

TODO: Phase 2 - asset_service를 새 스키마(Account, Entry) 기반으로 교체 예정.
현재는 스냅샷 생성을 건너뜁니다.
"""

import logging

from app.core.celery_app import celery_app
from app.core.tz import today as tz_today

logger = logging.getLogger(__name__)


@celery_app.task(name="app.tasks.snapshot_tasks.take_daily_snapshot")
def take_daily_snapshot():
    """모든 사용자의 자산 스냅샷을 일일 기록

    TODO: Phase 2 - asset_service가 삭제되어 현재 비활성 상태.
    새 Account/Entry 기반 자산 요약 서비스가 구현되면 복원 예정.
    """
    logger.info(
        "Daily snapshot skipped: asset_service removed during schema v2 migration. "
        "Will be restored in Phase 2."
    )
    return {"snapshots": 0, "date": str(tz_today()), "status": "skipped_phase2"}
