"""add ai_insights table

Revision ID: 006_add_ai_insights
Revises: 005_rm_expense_pm_tags
Create Date: 2026-02-18

"""
from alembic import op
import sqlalchemy as sa

revision = "006_add_ai_insights"
down_revision = "005_rm_expense_pm_tags"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "ai_insights",
        sa.Column("id", sa.Uuid(), primary_key=True),
        sa.Column(
            "user_id",
            sa.Uuid(),
            sa.ForeignKey("users.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("type", sa.String(20), nullable=False),
        sa.Column("title", sa.String(100), nullable=False),
        sa.Column("description", sa.String(500), nullable=False),
        sa.Column("severity", sa.String(10), nullable=False),
        sa.Column("generated_date", sa.Date(), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
        ),
    )
    op.create_index(
        "ix_ai_insights_user_date",
        "ai_insights",
        ["user_id", "generated_date"],
    )


def downgrade() -> None:
    op.drop_index("ix_ai_insights_user_date", table_name="ai_insights")
    op.drop_table("ai_insights")
