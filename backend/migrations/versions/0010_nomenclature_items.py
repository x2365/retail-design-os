"""П3: таблица nomenclature_items (номенклатура / ШК)

Revision ID: b0id3nomencl10
Revises: a9hc2rcfields09
Create Date: 2026-06-05
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

revision: str = "b0id3nomencl10"
down_revision: Union[str, None] = "a9hc2rcfields09"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "nomenclature_items",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("task_id", sa.Integer(), nullable=False),
        sa.Column("sku", sa.String(length=64), nullable=False, server_default=""),
        sa.Column("barcode", sa.String(length=64), nullable=False, server_default=""),
        sa.Column("name", sa.String(length=200), nullable=False, server_default=""),
        sa.Column("qty", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("status", sa.String(length=16), nullable=False, server_default="draft"),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.ForeignKeyConstraint(["task_id"], ["tasks.id"], ondelete="CASCADE"),
    )
    op.create_index("ix_nomenclature_task", "nomenclature_items", ["task_id"])
    op.create_index("ix_nomenclature_items_status", "nomenclature_items", ["status"])


def downgrade() -> None:
    op.drop_index("ix_nomenclature_items_status", table_name="nomenclature_items")
    op.drop_index("ix_nomenclature_task", table_name="nomenclature_items")
    op.drop_table("nomenclature_items")
