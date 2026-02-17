"""add investment_prompt to users

Revision ID: 002_add_investment_prompt
Revises: 001_initial
Create Date: 2026-02-16

"""
from alembic import op
import sqlalchemy as sa

revision = "002_add_investment_prompt"
down_revision = "001_initial"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("users", sa.Column("investment_prompt", sa.Text, nullable=True))


def downgrade() -> None:
    op.drop_column("users", "investment_prompt")
