"""phase4: import_batches and staged_entries

Revision ID: c2d3e4f5a6b7
Revises: b1c2d3e4f5a6
Create Date: 2026-07-07 00:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "c2d3e4f5a6b7"
down_revision: Union[str, None] = "b1c2d3e4f5a6"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "import_batches",
        sa.Column("id", sa.Uuid(), primary_key=True, nullable=False),
        sa.Column("user_id", sa.Uuid(), nullable=False),
        sa.Column("account_id", sa.Uuid(), nullable=True),
        sa.Column("filename", sa.String(length=255), nullable=False),
        sa.Column("file_hash", sa.String(length=64), nullable=False),
        sa.Column("source_bank", sa.String(length=50), nullable=True),
        sa.Column("status", sa.String(length=20), nullable=False),
        sa.Column("period_start", sa.Date(), nullable=True),
        sa.Column("period_end", sa.Date(), nullable=True),
        sa.Column("row_count", sa.Integer(), nullable=True),
        sa.Column("error", sa.Text(), nullable=True),
        sa.Column("raw_file", sa.LargeBinary(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["account_id"], ["accounts.id"], ondelete="SET NULL"),
        sa.UniqueConstraint("user_id", "file_hash", name="uq_import_batch_user_filehash"),
    )
    op.create_index("ix_import_batches_user_id", "import_batches", ["user_id"], unique=False)

    op.create_table(
        "staged_entries",
        sa.Column("id", sa.Uuid(), primary_key=True, nullable=False),
        sa.Column("batch_id", sa.Uuid(), nullable=False),
        sa.Column("user_id", sa.Uuid(), nullable=False),
        sa.Column("transacted_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("amount", sa.Numeric(18, 4), nullable=False),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("balance_after", sa.Numeric(18, 4), nullable=True),
        sa.Column("suggested_type", sa.String(length=20), nullable=True),
        sa.Column("suggested_category_id", sa.Uuid(), nullable=True),
        sa.Column("dedup_status", sa.String(length=20), nullable=False),
        sa.Column("matched_entry_id", sa.Uuid(), nullable=True),
        sa.Column("is_selected", sa.Boolean(), nullable=False),
        sa.Column("committed_entry_id", sa.Uuid(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["batch_id"], ["import_batches.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["suggested_category_id"], ["categories.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["matched_entry_id"], ["entries.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["committed_entry_id"], ["entries.id"], ondelete="SET NULL"),
    )
    op.create_index("ix_staged_entries_batch_id", "staged_entries", ["batch_id"], unique=False)
    op.create_index("ix_staged_entries_user_id", "staged_entries", ["user_id"], unique=False)


def downgrade() -> None:
    op.drop_index("ix_staged_entries_user_id", table_name="staged_entries")
    op.drop_index("ix_staged_entries_batch_id", table_name="staged_entries")
    op.drop_table("staged_entries")
    op.drop_index("ix_import_batches_user_id", table_name="import_batches")
    op.drop_table("import_batches")
