"""task stage check constraint (1..12)

Adds a DB-level CHECK so an out-of-range stage can never be persisted, even
outside the API. Stage values stay integers 1..12 (mapped to TaskStage IntEnum
in the application layer). Batch mode makes this work on SQLite too.

Revision ID: 33db2d23c22f
Revises: 025824d5dca2
Create Date: 2026-06-04
"""
from typing import Sequence, Union

from alembic import op

revision: str = "33db2d23c22f"
down_revision: Union[str, None] = "025824d5dca2"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    with op.batch_alter_table("tasks", schema=None) as batch_op:
        batch_op.create_check_constraint("ck_tasks_stage_range", "stage >= 1 AND stage <= 12")


def downgrade() -> None:
    with op.batch_alter_table("tasks", schema=None) as batch_op:
        batch_op.drop_constraint("ck_tasks_stage_range", type_="check")
