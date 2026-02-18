"""rename carryover_type 'investment' to 'transfer'

Revision ID: 011
Revises: 010
"""

from alembic import op

revision = "011_carryover_transfer"
down_revision = "010_source_asset"


def upgrade() -> None:
    op.execute(
        "UPDATE budget_carryover_settings SET carryover_type = 'transfer' WHERE carryover_type = 'investment'"
    )
    op.execute(
        "UPDATE budget_carryover_logs SET carryover_type = 'transfer' WHERE carryover_type = 'investment'"
    )


def downgrade() -> None:
    op.execute(
        "UPDATE budget_carryover_settings SET carryover_type = 'investment' WHERE carryover_type = 'transfer'"
    )
    op.execute(
        "UPDATE budget_carryover_logs SET carryover_type = 'investment' WHERE carryover_type = 'transfer'"
    )
