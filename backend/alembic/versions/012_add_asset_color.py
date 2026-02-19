"""add assets.color column

Revision ID: 012_asset_color
Revises: 011_carryover_transfer
Create Date: 2026-02-19

"""
from alembic import op
import sqlalchemy as sa

revision = "012_asset_color"
down_revision = "011_carryover_transfer"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "assets",
        sa.Column("color", sa.String(7), nullable=True),
    )


def downgrade() -> None:
    op.drop_column("assets", "color")
