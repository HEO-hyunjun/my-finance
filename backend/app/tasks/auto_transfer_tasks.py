import asyncio
import logging
from datetime import date

from app.core.celery_app import celery_app

logger = logging.getLogger(__name__)


@celery_app.task(name="app.tasks.auto_transfer_tasks.execute_auto_transfers")
def execute_auto_transfers():
    """자동이체 실행 (매일 transfer_day와 오늘 날짜 비교)"""
    return asyncio.run(_execute_auto_transfers_async())


async def _execute_auto_transfers_async():
    from sqlalchemy import select
    from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
    from sqlalchemy.orm import sessionmaker

    from app.core.config import settings
    from app.models.auto_transfer import AutoTransfer
    from app.services.transfer_service import execute_transfer

    engine = create_async_engine(settings.DATABASE_URL)
    async_session = sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)
    today = date.today()
    count = 0

    async with async_session() as db:
        result = await db.execute(
            select(AutoTransfer).where(
                AutoTransfer.is_active == True,
                AutoTransfer.transfer_day == today.day,
            )
        )
        items = result.scalars().all()

        for item in items:
            try:
                await execute_transfer(
                    db=db,
                    user_id=item.user_id,
                    source_asset_id=item.source_asset_id,
                    target_asset_id=item.target_asset_id,
                    amount=item.amount,
                    memo=f"[자동이체] {item.name}",
                )
                count += 1
            except Exception as e:
                logger.warning(
                    f"Auto transfer failed: {item.id} ({item.name}): {e}"
                )

    await engine.dispose()
    logger.info(f"Auto transfers executed: {count}/{len(items)} on {today}")
    return {"executed": count, "total": len(items), "date": str(today)}
