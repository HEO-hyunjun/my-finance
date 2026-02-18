"""add deposit/withdraw transaction types and source_asset_id

Revision ID: 007_deposit_withdraw
Revises: 006_add_ai_insights
Create Date: 2026-02-18

"""
from alembic import op
import sqlalchemy as sa

revision = "007_deposit_withdraw"
down_revision = "006_add_ai_insights"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "transactions",
        sa.Column(
            "source_asset_id",
            sa.Uuid(),
            sa.ForeignKey("assets.id", ondelete="SET NULL"),
            nullable=True,
        ),
    )


def downgrade() -> None:
    op.drop_column("transactions", "source_asset_id")
