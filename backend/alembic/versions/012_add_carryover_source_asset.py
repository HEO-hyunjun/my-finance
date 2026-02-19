"""Add source_asset_id to budget_carryover_settings

Revision ID: 012_carryover_source
Revises: 011_carryover_transfer
Create Date: 2026-02-20
"""

from alembic import op
import sqlalchemy as sa

revision = "012_carryover_source"
down_revision = "011_carryover_transfer"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "budget_carryover_settings",
        sa.Column("source_asset_id", sa.Uuid(), nullable=True),
    )
    op.create_foreign_key(
        "fk_carryover_source_asset",
        "budget_carryover_settings",
        "assets",
        ["source_asset_id"],
        ["id"],
        ondelete="SET NULL",
    )


def downgrade() -> None:
    op.drop_constraint("fk_carryover_source_asset", "budget_carryover_settings", type_="foreignkey")
    op.drop_column("budget_carryover_settings", "source_asset_id")
