"""remove payment_method and tags from expenses

Revision ID: 005_remove_expense_payment_method_tags
Revises: 004_add_asset_link
Create Date: 2026-02-18

"""
from alembic import op
import sqlalchemy as sa

revision = "005_remove_expense_payment_method_tags"
down_revision = "004_add_asset_link"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.drop_column("expenses", "payment_method")
    op.drop_column("expenses", "tags")


def downgrade() -> None:
    op.add_column("expenses", sa.Column("tags", sa.Text(), nullable=True))
    op.add_column(
        "expenses",
        sa.Column("payment_method", sa.String(20), nullable=True),
    )
