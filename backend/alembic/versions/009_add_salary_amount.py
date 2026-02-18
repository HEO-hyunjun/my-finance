"""add users.salary_amount column

Revision ID: 009_salary_amount
Revises: 008_auto_transfers
Create Date: 2026-02-18

"""
from alembic import op
import sqlalchemy as sa

revision = "009_salary_amount"
down_revision = "008_auto_transfers"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "users",
        sa.Column("salary_amount", sa.Integer(), nullable=True),
    )


def downgrade() -> None:
    op.drop_column("users", "salary_amount")
