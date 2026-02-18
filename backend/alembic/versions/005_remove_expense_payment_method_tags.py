"""remove payment_method and tags from expenses

Revision ID: 005_remove_expense_payment_method_tags
Revises: 004_add_asset_link
Create Date: 2026-02-18

"""
from alembic import op
import sqlalchemy as sa

revision = "005_rm_expense_pm_tags"
down_revision = "004_add_asset_link"
branch_labels = None
depends_on = None


def _column_exists(table: str, column: str) -> bool:
    bind = op.get_bind()
    insp = sa.inspect(bind)
    columns = [c["name"] for c in insp.get_columns(table)]
    return column in columns


def upgrade() -> None:
    if _column_exists("expenses", "payment_method"):
        op.drop_column("expenses", "payment_method")
    if _column_exists("expenses", "tags"):
        op.drop_column("expenses", "tags")


def downgrade() -> None:
    op.add_column("expenses", sa.Column("tags", sa.Text(), nullable=True))
    op.add_column(
        "expenses",
        sa.Column("payment_method", sa.String(20), nullable=True),
    )
