"""итерации дизайна (design_iteration)

Revision ID: c3ab6designiter23
Revises: b2za5shkjson22
Create Date: 2026-06-09
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

revision: str = "c3ab6designiter23"
down_revision: Union[str, None] = "b2za5shkjson22"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column("tasks", sa.Column("design_iteration", sa.Integer(), nullable=False, server_default="1"))


def downgrade() -> None:
    op.drop_column("tasks", "design_iteration")
