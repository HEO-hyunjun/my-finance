"""backfill: group-less BUY/SELL entries get a TRADE entry_group

Revision ID: d3e4f5a6b7c8
Revises: c2d3e4f5a6b7
Create Date: 2026-07-08 00:00:00.000000

"""
from typing import Sequence, Union

from alembic import op


revision: str = "d3e4f5a6b7c8"
down_revision: Union[str, None] = "c2d3e4f5a6b7"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # 옛 코드가 생성한 그룹 없는 BUY/SELL entry 각각에 TRADE entry_group을 만들어 링크.
    op.execute(
        """
        DO $$
        DECLARE r RECORD; gid uuid;
        BEGIN
          FOR r IN
            SELECT id, user_id, memo FROM entries
            WHERE type IN ('BUY', 'SELL') AND entry_group_id IS NULL
          LOOP
            gid := gen_random_uuid();
            INSERT INTO entry_groups (id, user_id, group_type, description, created_at)
            VALUES (gid, r.user_id, 'TRADE', left(r.memo, 200), now());
            UPDATE entries SET entry_group_id = gid WHERE id = r.id;
          END LOOP;
        END $$;
        """
    )


def downgrade() -> None:
    # 데이터 백필은 되돌리지 않는다 (백필로 생성된 그룹과 기존 그룹을 안전히 구분 불가).
    pass
