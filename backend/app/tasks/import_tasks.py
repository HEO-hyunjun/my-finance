import asyncio
import logging
import uuid

from app.core.celery_app import celery_app

logger = logging.getLogger(__name__)


def _get_async_session():
    from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
    from sqlalchemy.orm import sessionmaker
    from app.core.config import settings

    engine = create_async_engine(settings.DATABASE_URL)
    async_session = sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)
    return async_session, engine


@celery_app.task(name="app.tasks.import_tasks.parse_import_batch")
def parse_import_batch(batch_id: str, password: str | None = None):
    """업로드된 배치를 추출→LLM→중복판정 후 status=review로 전환."""
    return asyncio.run(_parse_import_batch_async(batch_id, password))


async def _parse_import_batch_async(batch_id: str, password: str | None):
    from app.models.import_batch import ImportBatch
    from app.services.import_service import parse_batch

    async_session, engine = _get_async_session()
    try:
        async with async_session() as db:
            bid = uuid.UUID(batch_id) if isinstance(batch_id, str) else batch_id
            batch = await db.get(ImportBatch, bid)
            if batch is None:
                logger.warning(f"Import batch not found: {batch_id}")
                return {"error": "batch not found"}
            await parse_batch(db, batch, password=password)
            await db.commit()
            logger.info(f"Import batch {batch_id} parsed: status={batch.status}")
            return {"batch_id": str(batch.id), "status": batch.status}
    finally:
        await engine.dispose()
