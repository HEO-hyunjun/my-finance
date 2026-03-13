"""Add recurring_incomes table and refactor income recurring fields

Revision ID: 014_recurring_income
Revises: 013_expense_cat_null
Create Date: 2026-03-13
"""

from alembic import op
import sqlalchemy as sa

revision = "014_recurring_income"
down_revision = "013_expense_cat_null"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # 1. recurring_incomes 테이블 생성
    op.create_table(
        "recurring_incomes",
        sa.Column("id", sa.CHAR(36), primary_key=True),
        sa.Column("user_id", sa.CHAR(36), sa.ForeignKey("users.id", ondelete="CASCADE"), nullable=False),
        sa.Column("type", sa.String(20), nullable=False),
        sa.Column("amount", sa.Numeric(18, 0), nullable=False),
        sa.Column("description", sa.String(200), nullable=False),
        sa.Column("recurring_day", sa.Integer, nullable=False),
        sa.Column("target_asset_id", sa.CHAR(36), sa.ForeignKey("assets.id", ondelete="SET NULL"), nullable=True),
        sa.Column("is_active", sa.Boolean, nullable=False, server_default="1"),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
    )
    op.create_index("ix_recurring_incomes_target_asset_id", "recurring_incomes", ["target_asset_id"])

    # 2. incomes 테이블에 recurring_income_id 컬럼 추가
    op.add_column(
        "incomes",
        sa.Column("recurring_income_id", sa.CHAR(36), nullable=True),
    )
    op.create_foreign_key(
        "fk_incomes_recurring_income_id",
        "incomes",
        "recurring_incomes",
        ["recurring_income_id"],
        ["id"],
        ondelete="SET NULL",
    )
    op.create_index("ix_incomes_recurring_income_id", "incomes", ["recurring_income_id"])

    # 3. 기존 is_recurring=True 레코드를 recurring_incomes로 마이그레이션
    # 유저+타입+recurring_day 기준으로 최신 1건씩만 템플릿으로 이관
    conn = op.get_bind()

    # is_recurring 컬럼이 존재하는 경우에만 마이그레이션 실행
    recurring_rows = conn.execute(
        sa.text("""
            SELECT id, user_id, type, amount, description, recurring_day, target_asset_id, created_at
            FROM incomes
            WHERE is_recurring = 1 AND recurring_day IS NOT NULL
            ORDER BY received_at DESC
        """)
    ).fetchall()

    # 유저+타입+recurring_day 기준 중복 제거
    seen = set()
    for row in recurring_rows:
        key = (row[1], row[2], row[5])  # user_id, type, recurring_day
        if key in seen:
            continue
        seen.add(key)

        import uuid
        ri_id = str(uuid.uuid4())
        conn.execute(
            sa.text("""
                INSERT INTO recurring_incomes (id, user_id, type, amount, description, recurring_day, target_asset_id, is_active, created_at, updated_at)
                VALUES (:id, :user_id, :type, :amount, :description, :recurring_day, :target_asset_id, 1, :created_at, :created_at)
            """),
            {
                "id": ri_id,
                "user_id": row[1],
                "type": row[2],
                "amount": row[3],
                "description": row[4],
                "recurring_day": row[5],
                "target_asset_id": row[6],
                "created_at": row[7],
            },
        )

        # 해당 유저+타입+recurring_day의 모든 기존 is_recurring 레코드에 recurring_income_id 연결
        conn.execute(
            sa.text("""
                UPDATE incomes
                SET recurring_income_id = :ri_id
                WHERE user_id = :user_id AND type = :type AND recurring_day = :recurring_day AND is_recurring = 1
            """),
            {
                "ri_id": ri_id,
                "user_id": row[1],
                "type": row[2],
                "recurring_day": row[5],
            },
        )

    # 4. 기존 컬럼 삭제
    op.drop_column("incomes", "is_recurring")
    op.drop_column("incomes", "recurring_day")


def downgrade() -> None:
    # 1. is_recurring, recurring_day 컬럼 복원
    op.add_column("incomes", sa.Column("is_recurring", sa.Boolean, nullable=False, server_default="0"))
    op.add_column("incomes", sa.Column("recurring_day", sa.Integer, nullable=True))

    # 2. recurring_income_id가 있는 레코드에 is_recurring=True 복원
    conn = op.get_bind()
    conn.execute(
        sa.text("""
            UPDATE incomes i
            JOIN recurring_incomes ri ON i.recurring_income_id = ri.id
            SET i.is_recurring = 1, i.recurring_day = ri.recurring_day
            WHERE i.recurring_income_id IS NOT NULL
        """)
    )

    # 3. recurring_income_id 컬럼 및 FK 삭제
    op.drop_index("ix_incomes_recurring_income_id", table_name="incomes")
    op.drop_constraint("fk_incomes_recurring_income_id", "incomes", type_="foreignkey")
    op.drop_column("incomes", "recurring_income_id")

    # 4. recurring_incomes 테이블 삭제
    op.drop_index("ix_recurring_incomes_target_asset_id", table_name="recurring_incomes")
    op.drop_table("recurring_incomes")
