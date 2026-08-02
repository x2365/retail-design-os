"""карточка ШК как JSON (shk_data)

Revision ID: b2za5shkjson22
Revises: a1yz4teamcontact21
Create Date: 2026-06-09
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

revision: str = "b2za5shkjson22"
down_revision: Union[str, None] = "a1yz4teamcontact21"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column("tasks", sa.Column("shk_data", sa.Text(), nullable=False, server_default=""))


def downgrade() -> None:
    op.drop_column("tasks", "shk_data")
