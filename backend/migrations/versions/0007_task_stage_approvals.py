"""task_stage_approvals (таблица вместо JSON tasks.stage_approvals)

Создаёт таблицу согласований по этапам, переносит данные из JSON-поля
tasks.stage_approvals в строки и удаляет JSON-поле.

Revision ID: e7fa9appr007
Revises: d6e8hist0006
Create Date: 2026-06-05
"""
import json
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

revision: str = "e7fa9appr007"
down_revision: Union[str, None] = "d6e8hist0006"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "task_stage_approvals",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("task_id", sa.Integer(), nullable=False),
        sa.Column("stage", sa.Integer(), nullable=False),
        sa.Column("approved", sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.Column("user_id", sa.Integer(), nullable=True),
        sa.Column("comment", sa.String(length=300), nullable=True),
        sa.Column("approved_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.ForeignKeyConstraint(["task_id"], ["tasks.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="SET NULL"),
        sa.UniqueConstraint("task_id", "stage", name="uq_stage_approval_task_stage"),
    )
    op.create_index("ix_stage_approval_task", "task_stage_approvals", ["task_id"])

    # перенос данных из JSON {"1": true, "2": false, ...} в строки
    bind = op.get_bind()
    rows = bind.execute(sa.text("SELECT id, stage_approvals FROM tasks")).fetchall()
    ins = sa.text(
        "INSERT INTO task_stage_approvals (task_id, stage, approved) "
        "VALUES (:tid, :stage, :appr)"
    )
    for task_id, raw in rows:
        if not raw:
            continue
        data = raw if isinstance(raw, dict) else json.loads(raw)
        for stage_str, val in data.items():
            bind.execute(ins, {"tid": task_id, "stage": int(stage_str), "appr": bool(val)})

    with op.batch_alter_table("tasks", schema=None) as b:
        b.drop_column("stage_approvals")


def downgrade() -> None:
    with op.batch_alter_table("tasks", schema=None) as b:
        b.add_column(sa.Column("stage_approvals", sa.JSON(), nullable=True))

    # собрать JSON обратно из строк
    bind = op.get_bind()
    rows = bind.execute(
        sa.text("SELECT task_id, stage, approved FROM task_stage_approvals ORDER BY task_id, stage")
    ).fetchall()
    by_task: dict[int, dict] = {}
    for task_id, stage, approved in rows:
        by_task.setdefault(task_id, {})[str(stage)] = bool(approved)
    upd = sa.text("UPDATE tasks SET stage_approvals = :j WHERE id = :tid")
    for task_id, mapping in by_task.items():
        bind.execute(upd, {"j": json.dumps(mapping), "tid": task_id})

    op.drop_index("ix_stage_approval_task", table_name="task_stage_approvals")
    op.drop_table("task_stage_approvals")
