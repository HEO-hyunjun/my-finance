"""add source_asset_id to expenses and target_asset_id to incomes

Revision ID: 004_add_asset_link
Revises: 003_add_expense_fixed_expense_id
Create Date: 2026-02-18

"""
from alembic import op
import sqlalchemy as sa

revision = "004_add_asset_link"
down_revision = "003_add_expense_fixed_expense_id"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # expenses.source_asset_id
    op.add_column(
        "expenses",
        sa.Column("source_asset_id", sa.Uuid(), nullable=True),
    )
    op.create_index(
        "ix_expenses_source_asset_id",
        "expenses",
        ["source_asset_id"],
    )
    op.create_foreign_key(
        "fk_expenses_source_asset_id",
        "expenses",
        "assets",
        ["source_asset_id"],
        ["id"],
        ondelete="SET NULL",
    )

    # incomes.target_asset_id
    op.add_column(
        "incomes",
        sa.Column("target_asset_id", sa.Uuid(), nullable=True),
    )
    op.create_index(
        "ix_incomes_target_asset_id",
        "incomes",
        ["target_asset_id"],
    )
    op.create_foreign_key(
        "fk_incomes_target_asset_id",
        "incomes",
        "assets",
        ["target_asset_id"],
        ["id"],
        ondelete="SET NULL",
    )


def downgrade() -> None:
    # incomes
    op.drop_constraint("fk_incomes_target_asset_id", "incomes", type_="foreignkey")
    op.drop_index("ix_incomes_target_asset_id", table_name="incomes")
    op.drop_column("incomes", "target_asset_id")

    # expenses
    op.drop_constraint("fk_expenses_source_asset_id", "expenses", type_="foreignkey")
    op.drop_index("ix_expenses_source_asset_id", table_name="expenses")
    op.drop_column("expenses", "source_asset_id")
