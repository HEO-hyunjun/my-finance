"""replace payment_method with source_asset_id in fixed_expenses and installments

Revision ID: 010
Revises: 009
"""

from alembic import op
import sqlalchemy as sa

revision = "010_source_asset"
down_revision = "009_salary_amount"


def upgrade() -> None:
    # fixed_expenses: add source_asset_id, remove payment_method
    op.add_column(
        "fixed_expenses",
        sa.Column("source_asset_id", sa.Uuid(), sa.ForeignKey("assets.id", ondelete="SET NULL"), nullable=True),
    )
    op.create_index("ix_fixed_expenses_source_asset_id", "fixed_expenses", ["source_asset_id"])
    op.drop_column("fixed_expenses", "payment_method")

    # installments: add source_asset_id, remove payment_method
    op.add_column(
        "installments",
        sa.Column("source_asset_id", sa.Uuid(), sa.ForeignKey("assets.id", ondelete="SET NULL"), nullable=True),
    )
    op.create_index("ix_installments_source_asset_id", "installments", ["source_asset_id"])
    op.drop_column("installments", "payment_method")


def downgrade() -> None:
    # installments: restore payment_method, remove source_asset_id
    op.add_column(
        "installments",
        sa.Column("payment_method", sa.String(20), nullable=True),
    )
    op.drop_index("ix_installments_source_asset_id", "installments")
    op.drop_column("installments", "source_asset_id")

    # fixed_expenses: restore payment_method, remove source_asset_id
    op.add_column(
        "fixed_expenses",
        sa.Column("payment_method", sa.String(20), nullable=True),
    )
    op.drop_index("ix_fixed_expenses_source_asset_id", "fixed_expenses")
    op.drop_column("fixed_expenses", "source_asset_id")
