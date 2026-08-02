"""журнал изменений: audit_log

Revision ID: f4mn7audit14
Revises: e3lm6shipdoc13
Create Date: 2026-06-08
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

revision: str = "f4mn7audit14"
down_revision: Union[str, None] = "e3lm6shipdoc13"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "audit_log",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("user_id", sa.Integer(), nullable=True),
        sa.Column("user_name", sa.String(length=150), nullable=False, server_default=""),
        sa.Column("entity_type", sa.String(length=24), nullable=False),
        sa.Column("entity_code", sa.String(length=32), nullable=False),
        sa.Column("field", sa.String(length=40), nullable=False),
        sa.Column("old_value", sa.String(length=120), nullable=False, server_default=""),
        sa.Column("new_value", sa.String(length=120), nullable=False, server_default=""),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="SET NULL"),
    )
    op.create_index("ix_audit_entity", "audit_log", ["entity_type", "entity_code"])


def downgrade() -> None:
    op.drop_index("ix_audit_entity", table_name="audit_log")
    op.drop_table("audit_log")
