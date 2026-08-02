"""полный бриф/ТЗ как JSON (brief_data)

Revision ID: f0xy3briefjson20
Revises: e9wx2sampleprod19
Create Date: 2026-06-09
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

revision: str = "f0xy3briefjson20"
down_revision: Union[str, None] = "e9wx2sampleprod19"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column("tasks", sa.Column("brief_data", sa.Text(), nullable=False, server_default=""))


def downgrade() -> None:
    op.drop_column("tasks", "brief_data")
