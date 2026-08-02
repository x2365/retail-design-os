"""documents: task_id nullable + equipment_id (файлы карточки библиотеки)

Документ теперь принадлежит задаче (этап) ИЛИ карточке библиотеки (полный файл
проекта). Добавляет equipment_id (FK→equipment, CASCADE), делает task_id
nullable и ставит CHECK, что задан хотя бы один владелец.

Revision ID: b2d4lib0004
Revises: a1c3f0money03
Create Date: 2026-06-05
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

revision: str = "b2d4lib0004"
down_revision: Union[str, None] = "a1c3f0money03"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    with op.batch_alter_table("documents", schema=None) as b:
        b.add_column(sa.Column("equipment_id", sa.Integer(), nullable=True))
        b.alter_column("task_id", existing_type=sa.Integer(), nullable=True)
        b.create_foreign_key(
            "fk_documents_equipment", "equipment", ["equipment_id"], ["id"], ondelete="CASCADE"
        )
        b.create_index("ix_documents_equipment", ["equipment_id"])
        b.create_check_constraint(
            "ck_documents_owner", "task_id IS NOT NULL OR equipment_id IS NOT NULL"
        )


def downgrade() -> None:
    with op.batch_alter_table("documents", schema=None) as b:
        b.drop_constraint("ck_documents_owner", type_="check")
        b.drop_index("ix_documents_equipment")
        b.drop_constraint("fk_documents_equipment", type_="foreignkey")
        b.alter_column("task_id", existing_type=sa.Integer(), nullable=False)
        b.drop_column("equipment_id")
