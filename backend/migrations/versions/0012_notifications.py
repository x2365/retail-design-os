"""напоминания: users.telegram_chat_id + таблица notifications

Revision ID: d2kf5notify12
Revises: c1je4apprcom11
Create Date: 2026-06-07
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

revision: str = "d2kf5notify12"
down_revision: Union[str, None] = "c1je4apprcom11"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    with op.batch_alter_table("users", schema=None) as b:
        b.add_column(sa.Column("telegram_chat_id", sa.String(length=40), nullable=True))

    op.create_table(
        "notifications",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("user_id", sa.Integer(), nullable=True),
        sa.Column("task_id", sa.Integer(), nullable=True),
        sa.Column("stage", sa.Integer(), nullable=True),
        sa.Column("rule", sa.String(length=32), nullable=False),
        sa.Column("message", sa.String(length=500), nullable=False),
        sa.Column("dedup_key", sa.String(length=160), nullable=False),
        sa.Column("status", sa.String(length=16), nullable=False, server_default="pending"),
        sa.Column("channels", sa.String(length=120), nullable=False, server_default=""),
        sa.Column("sent_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["task_id"], ["tasks.id"], ondelete="CASCADE"),
    )
    op.create_index("ix_notifications_user", "notifications", ["user_id"])
    op.create_index("ix_notifications_status", "notifications", ["status"])
    op.create_index("ix_notifications_dedup", "notifications", ["dedup_key"], unique=True)


def downgrade() -> None:
    op.drop_index("ix_notifications_dedup", table_name="notifications")
    op.drop_index("ix_notifications_status", table_name="notifications")
    op.drop_index("ix_notifications_user", table_name="notifications")
    op.drop_table("notifications")
    with op.batch_alter_table("users", schema=None) as b:
        b.drop_column("telegram_chat_id")
