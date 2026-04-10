import asyncio
from logging.config import fileConfig

from alembic import context
from sqlalchemy import pool
from sqlalchemy.ext.asyncio import async_engine_from_config

from app.core.config import settings
from app.core.database import Base

# Import all models so Alembic can detect them
from app.models.user import User  # noqa: F401
from app.models.account import Account  # noqa: F401
from app.models.security import Security, SecurityPrice  # noqa: F401
from app.models.entry import Entry, EntryGroup  # noqa: F401
from app.models.category import Category  # noqa: F401
from app.models.recurring_schedule import RecurringSchedule  # noqa: F401
from app.models.budget_v2 import BudgetPeriod, BudgetAllocation  # noqa: F401
from app.models.portfolio import (  # noqa: F401
    AssetSnapshot, PortfolioTarget, RebalancingAlert, GoalAsset, AccountSnapshot,
)
from app.models.settings import ApiKey, LlmSetting  # noqa: F401
from app.models.conversation import Conversation  # noqa: F401
from app.models.insight import AIInsightRecord  # noqa: F401

config = context.config
config.set_main_option("sqlalchemy.url", settings.DATABASE_URL)

if config.config_file_name is not None:
    fileConfig(config.config_file_name)

target_metadata = Base.metadata


def run_migrations_offline() -> None:
    url = config.get_main_option("sqlalchemy.url")
    context.configure(
        url=url,
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
    )
    with context.begin_transaction():
        context.run_migrations()


def do_run_migrations(connection):
    context.configure(connection=connection, target_metadata=target_metadata)
    with context.begin_transaction():
        context.run_migrations()


async def run_async_migrations() -> None:
    connectable = async_engine_from_config(
        config.get_section(config.config_ini_section, {}),
        prefix="sqlalchemy.",
        poolclass=pool.NullPool,
    )
    async with connectable.connect() as connection:
        await connection.run_sync(do_run_migrations)
    await connectable.dispose()


def run_migrations_online() -> None:
    asyncio.run(run_async_migrations())


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
