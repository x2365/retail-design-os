"""approvals.comment (комментарий к согласованию)

Revision ID: c1je4apprcom11
Revises: b0id3nomencl10
Create Date: 2026-06-06
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

revision: str = "c1je4apprcom11"
down_revision: Union[str, None] = "b0id3nomencl10"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    with op.batch_alter_table("approvals", schema=None) as b:
        b.add_column(sa.Column("comment", sa.String(length=500), nullable=True))


def downgrade() -> None:
    with op.batch_alter_table("approvals", schema=None) as b:
        b.drop_column("comment")
