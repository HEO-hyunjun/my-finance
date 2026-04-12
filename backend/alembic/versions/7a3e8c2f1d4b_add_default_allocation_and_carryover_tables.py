"""add default_allocation to categories and create carryover_settings/logs

Revision ID: 7a3e8c2f1d4b
Revises: 5d9d1b08fe59
Create Date: 2026-04-13 00:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "7a3e8c2f1d4b"
down_revision: Union[str, None] = "5d9d1b08fe59"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


CARRYOVER_TYPE_ENUM = sa.Enum(
    "expire",
    "next_month",
    "savings",
    "deposit",
    "transfer",
    name="carryovertype",
)


def upgrade() -> None:
    op.add_column(
        "categories",
        sa.Column("default_allocation", sa.Numeric(18, 4), nullable=True),
    )

    CARRYOVER_TYPE_ENUM.create(op.get_bind(), checkfirst=True)

    op.create_table(
        "carryover_settings",
        sa.Column("id", sa.Uuid(), primary_key=True, nullable=False),
        sa.Column("user_id", sa.Uuid(), nullable=False),
        sa.Column("category_id", sa.Uuid(), nullable=False),
        sa.Column(
            "carryover_type",
            sa.Enum(
                "expire", "next_month", "savings", "deposit", "transfer",
                name="carryovertype",
                create_type=False,
            ),
            nullable=False,
        ),
        sa.Column("carryover_limit", sa.Numeric(18, 4), nullable=True),
        sa.Column("source_asset_id", sa.Uuid(), nullable=True),
        sa.Column("target_asset_id", sa.Uuid(), nullable=True),
        sa.Column("target_savings_name", sa.String(100), nullable=True),
        sa.Column("target_annual_rate", sa.Numeric(5, 3), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=True),
        sa.ForeignKeyConstraint(["category_id"], ["categories.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["source_asset_id"], ["accounts.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["target_asset_id"], ["accounts.id"], ondelete="SET NULL"),
        sa.UniqueConstraint("user_id", "category_id", name="uq_carryover_setting_user_category"),
    )
    op.create_index(
        "ix_carryover_settings_user_id",
        "carryover_settings",
        ["user_id"],
        unique=False,
    )

    op.create_table(
        "carryover_logs",
        sa.Column("id", sa.Uuid(), primary_key=True, nullable=False),
        sa.Column("user_id", sa.Uuid(), nullable=False),
        sa.Column("category_id", sa.Uuid(), nullable=False),
        sa.Column("budget_period_start", sa.Date(), nullable=False),
        sa.Column("budget_period_end", sa.Date(), nullable=False),
        sa.Column(
            "carryover_type",
            sa.Enum(
                "expire", "next_month", "savings", "deposit", "transfer",
                name="carryovertype",
                create_type=False,
            ),
            nullable=False,
        ),
        sa.Column("amount", sa.Numeric(18, 4), nullable=False),
        sa.Column("target_description", sa.String(200), nullable=True),
        sa.Column("executed_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=True),
        sa.ForeignKeyConstraint(["category_id"], ["categories.id"], ondelete="CASCADE"),
    )
    op.create_index(
        "ix_carryover_logs_user_id",
        "carryover_logs",
        ["user_id"],
        unique=False,
    )


def downgrade() -> None:
    op.drop_index("ix_carryover_logs_user_id", table_name="carryover_logs")
    op.drop_table("carryover_logs")
    op.drop_index("ix_carryover_settings_user_id", table_name="carryover_settings")
    op.drop_table("carryover_settings")
    CARRYOVER_TYPE_ENUM.drop(op.get_bind(), checkfirst=True)
    op.drop_column("categories", "default_allocation")
