"""phase2: user_id FK, entries.source, loan/credit_card, account check, portfolio_target domain

Revision ID: b1c2d3e4f5a6
Revises: 7a3e8c2f1d4b
Create Date: 2026-07-07 00:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "b1c2d3e4f5a6"
down_revision: Union[str, None] = "7a3e8c2f1d4b"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


# user_id FK를 추가할 테이블 (H)
_USER_FK_TABLES = [
    "accounts",
    "entries",
    "entry_groups",
    "categories",
    "recurring_schedules",
    "budget_periods",
    "budget_allocations",
]


def upgrade() -> None:
    # 1) AccountType에 loan/credit_card 추가 (enum ADD VALUE는 트랜잭션 밖에서)
    with op.get_context().autocommit_block():
        op.execute("ALTER TYPE accounttype ADD VALUE IF NOT EXISTS 'LOAN'")
        op.execute("ALTER TYPE accounttype ADD VALUE IF NOT EXISTS 'CREDIT_CARD'")

    # 2) entries.source 컬럼 + 백필
    op.add_column("entries", sa.Column("source", sa.String(length=20), nullable=True))
    op.execute(
        "UPDATE entries SET source='recurring' "
        "WHERE recurring_schedule_id IS NOT NULL AND source IS NULL"
    )
    op.execute(
        "UPDATE entries SET source='interest' "
        "WHERE source IS NULL AND (memo LIKE '%일일이자%' OR memo LIKE '%월별이자%')"
    )

    # 3) user_id FK (CASCADE)
    for table in _USER_FK_TABLES:
        op.create_foreign_key(
            f"fk_{table}_user_id_users",
            table,
            "users",
            ["user_id"],
            ["id"],
            ondelete="CASCADE",
        )

    # 4) Account 상품속성 CHECK: monthly_amount는 적금(savings)에만
    op.execute(
        "UPDATE accounts SET monthly_amount = NULL "
        "WHERE monthly_amount IS NOT NULL AND account_type <> 'SAVINGS'"
    )
    op.create_check_constraint(
        "ck_account_monthly_amount_savings",
        "accounts",
        "monthly_amount IS NULL OR account_type = 'SAVINGS'",
    )

    # 5) PortfolioTarget.asset_type 도메인 이전 (parking→cash, savings→deposit,
    #    investment→재설정 필요). unique(user_id, asset_type) 충돌 시 target_ratio 합산.
    #    savings→deposit
    op.execute(
        "UPDATE portfolio_targets d SET target_ratio = d.target_ratio + s.target_ratio "
        "FROM portfolio_targets s "
        "WHERE s.user_id = d.user_id AND d.asset_type='deposit' AND s.asset_type='savings'"
    )
    op.execute(
        "DELETE FROM portfolio_targets pt WHERE pt.asset_type='savings' "
        "AND EXISTS (SELECT 1 FROM portfolio_targets d "
        "WHERE d.user_id=pt.user_id AND d.asset_type='deposit')"
    )
    op.execute("UPDATE portfolio_targets SET asset_type='deposit' WHERE asset_type='savings'")
    #    parking→cash
    op.execute(
        "UPDATE portfolio_targets c SET target_ratio = c.target_ratio + p.target_ratio "
        "FROM portfolio_targets p "
        "WHERE p.user_id = c.user_id AND c.asset_type='cash' AND p.asset_type='parking'"
    )
    op.execute(
        "DELETE FROM portfolio_targets pt WHERE pt.asset_type='parking' "
        "AND EXISTS (SELECT 1 FROM portfolio_targets c "
        "WHERE c.user_id=pt.user_id AND c.asset_type='cash')"
    )
    op.execute("UPDATE portfolio_targets SET asset_type='cash' WHERE asset_type='parking'")
    #    investment → 재설정 필요 센티넬
    op.execute(
        "UPDATE portfolio_targets SET asset_type='__needs_reset__' WHERE asset_type='investment'"
    )


def downgrade() -> None:
    # 데이터 이전(2-1.5)과 enum ADD VALUE는 되돌리지 않음 (Postgres enum 값 삭제 불가).
    op.drop_constraint("ck_account_monthly_amount_savings", "accounts", type_="check")

    for table in _USER_FK_TABLES:
        op.drop_constraint(f"fk_{table}_user_id_users", table, type_="foreignkey")

    op.drop_column("entries", "source")
