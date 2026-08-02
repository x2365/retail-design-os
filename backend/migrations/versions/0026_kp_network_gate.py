"""kp network approval gate (third)

Revision ID: f6de9kpnetwork26
Revises: e5cd8contractordet25
"""
from __future__ import annotations
from typing import Union
import sqlalchemy as sa
from alembic import op

revision: str = "f6de9kpnetwork26"
down_revision: Union[str, None] = "e5cd8contractordet25"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("tasks", sa.Column("kp_network_approved_by", sa.String(length=150), nullable=False, server_default=""))
    op.add_column("tasks", sa.Column("kp_network_approved_at", sa.DateTime(timezone=True), nullable=True))


def downgrade() -> None:
    op.drop_column("tasks", "kp_network_approved_at")
    op.drop_column("tasks", "kp_network_approved_by")
