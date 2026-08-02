"""task_stage_history (журнал переходов этапов)

Лог всех переходов между этапами задачи (кто/когда/откуда-куда).
from_stage = NULL — исходная запись при создании задачи.

Revision ID: d6e8hist0006
Revises: c5da7e0utc05
Create Date: 2026-06-05
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

revision: str = "d6e8hist0006"
down_revision: Union[str, None] = "c5da7e0utc05"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "task_stage_history",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("task_id", sa.Integer(), nullable=False),
        sa.Column("from_stage", sa.Integer(), nullable=True),
        sa.Column("to_stage", sa.Integer(), nullable=False),
        sa.Column("user_id", sa.Integer(), nullable=True),
        sa.Column("comment", sa.String(length=300), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.ForeignKeyConstraint(["task_id"], ["tasks.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="SET NULL"),
    )
    op.create_index("ix_stage_history_task", "task_stage_history", ["task_id"])


def downgrade() -> None:
    op.drop_index("ix_stage_history_task", table_name="task_stage_history")
    op.drop_table("task_stage_history")
