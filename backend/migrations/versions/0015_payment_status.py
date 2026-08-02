"""ручной статус оплаты задачи: payment_status

Revision ID: a5pq8paystat15
Revises: f4mn7audit14
Create Date: 2026-06-08
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

revision: str = "a5pq8paystat15"
down_revision: Union[str, None] = "f4mn7audit14"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        "tasks",
        sa.Column("payment_status", sa.String(length=16), nullable=False, server_default="unpaid"),
    )


def downgrade() -> None:
    op.drop_column("tasks", "payment_status")
