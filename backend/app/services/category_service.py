import uuid

from fastapi import HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.category import Category


async def create_category(db: AsyncSession, user_id: uuid.UUID, data: dict) -> Category:
    category = Category(user_id=user_id, **data)
    db.add(category)
    await db.commit()
    await db.refresh(category)
    return category


async def get_categories(db: AsyncSession, user_id: uuid.UUID, direction: str | None = None) -> list[Category]:
    stmt = select(Category).where(Category.user_id == user_id)
    if direction:
        stmt = stmt.where(Category.direction == direction)
    stmt = stmt.order_by(Category.sort_order)
    return list((await db.execute(stmt)).scalars().all())


async def get_category(db: AsyncSession, user_id: uuid.UUID, category_id: uuid.UUID) -> Category:
    stmt = select(Category).where(Category.id == category_id, Category.user_id == user_id)
    category = (await db.execute(stmt)).scalar_one_or_none()
    if not category:
        raise HTTPException(status_code=404, detail="Category not found")
    return category


async def update_category(db: AsyncSession, user_id: uuid.UUID, category_id: uuid.UUID, data: dict) -> Category:
    category = await get_category(db, user_id, category_id)
    for field, value in data.items():
        setattr(category, field, value)
    await db.commit()
    await db.refresh(category)
    return category


async def delete_category(db: AsyncSession, user_id: uuid.UUID, category_id: uuid.UUID) -> None:
    category = await get_category(db, user_id, category_id)
    await db.delete(category)
    await db.commit()
