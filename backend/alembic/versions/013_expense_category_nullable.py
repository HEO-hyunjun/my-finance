"""Make expense category_id nullable for uncategorized expenses

Revision ID: 013_expense_cat_null
Revises: 012_carryover_source
Create Date: 2026-03-08
"""

from alembic import op
import sqlalchemy as sa

revision = "013_expense_cat_null"
down_revision = "012_carryover_source"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Drop the existing foreign key constraint (MySQL auto-generated name)
    op.drop_constraint(
        "expenses_ibfk_2", "expenses", type_="foreignkey"
    )
    # Alter column to nullable
    op.alter_column(
        "expenses",
        "category_id",
        existing_type=sa.CHAR(36),
        nullable=True,
    )
    # Re-create foreign key with SET NULL on delete
    op.create_foreign_key(
        "expenses_ibfk_2",
        "expenses",
        "budget_categories",
        ["category_id"],
        ["id"],
        ondelete="SET NULL",
    )


def downgrade() -> None:
    # Drop SET NULL foreign key
    op.drop_constraint(
        "expenses_ibfk_2", "expenses", type_="foreignkey"
    )
    # Alter column back to non-nullable
    op.alter_column(
        "expenses",
        "category_id",
        existing_type=sa.CHAR(36),
        nullable=False,
    )
    # Re-create original CASCADE foreign key
    op.create_foreign_key(
        "expenses_ibfk_2",
        "expenses",
        "budget_categories",
        ["category_id"],
        ["id"],
        ondelete="CASCADE",
    )
