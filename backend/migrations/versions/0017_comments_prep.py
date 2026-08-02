"""комментарии к задаче + согласования этапа «Подготовка»

Revision ID: c7tu0prepcom17
Revises: b6rs9brief16
Create Date: 2026-06-08
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

revision: str = "c7tu0prepcom17"
down_revision: Union[str, None] = "b6rs9brief16"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "comments",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("task_id", sa.Integer(), nullable=False),
        sa.Column("author_id", sa.Integer(), nullable=True),
        sa.Column("author_name", sa.String(length=150), nullable=False, server_default=""),
        sa.Column("text", sa.Text(), nullable=False, server_default=""),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.ForeignKeyConstraint(["task_id"], ["tasks.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["author_id"], ["users.id"], ondelete="SET NULL"),
    )
    op.create_index("ix_comments_task_id", "comments", ["task_id"])
    op.add_column("tasks", sa.Column("prep_brand_approved_by", sa.String(length=150), nullable=False, server_default=""))
    op.add_column("tasks", sa.Column("prep_brand_approved_at", sa.DateTime(timezone=True), nullable=True))
    op.add_column("tasks", sa.Column("prep_zya_approved_by", sa.String(length=150), nullable=False, server_default=""))
    op.add_column("tasks", sa.Column("prep_zya_approved_at", sa.DateTime(timezone=True), nullable=True))


def downgrade() -> None:
    for col in ("prep_zya_approved_at", "prep_zya_approved_by", "prep_brand_approved_at", "prep_brand_approved_by"):
        op.drop_column("tasks", col)
    op.drop_index("ix_comments_task_id", table_name="comments")
    op.drop_table("comments")
