"""ответственные за этап (stage_responsible)

Revision ID: d4bc7stageresp24
Revises: c3ab6designiter23
Create Date: 2026-06-10
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

revision: str = "d4bc7stageresp24"
down_revision: Union[str, None] = "c3ab6designiter23"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column("tasks", sa.Column("stage_responsible", sa.Text(), nullable=False, server_default=""))


def downgrade() -> None:
    op.drop_column("tasks", "stage_responsible")
