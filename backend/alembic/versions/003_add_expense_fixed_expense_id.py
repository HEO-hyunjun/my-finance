"""add fixed_expense_id to expenses

Revision ID: 003_add_expense_fixed_expense_id
Revises: 002_add_investment_prompt
Create Date: 2026-02-18

"""
from alembic import op
import sqlalchemy as sa

revision = "003_add_expense_fixed_expense_id"
down_revision = "002_add_investment_prompt"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "expenses",
        sa.Column("fixed_expense_id", sa.Uuid(), nullable=True),
    )
    op.create_index(
        "ix_expenses_fixed_expense_id",
        "expenses",
        ["fixed_expense_id"],
    )
    op.create_foreign_key(
        "fk_expenses_fixed_expense_id",
        "expenses",
        "fixed_expenses",
        ["fixed_expense_id"],
        ["id"],
        ondelete="SET NULL",
    )


def downgrade() -> None:
    op.drop_constraint("fk_expenses_fixed_expense_id", "expenses", type_="foreignkey")
    op.drop_index("ix_expenses_fixed_expense_id", table_name="expenses")
    op.drop_column("expenses", "fixed_expense_id")
