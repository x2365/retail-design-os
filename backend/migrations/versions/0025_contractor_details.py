"""contractor details json

Revision ID: e5cd8contractordet25
Revises: d4bc7stageresp24
"""
from __future__ import annotations
from typing import Union
import sqlalchemy as sa
from alembic import op

revision: str = "e5cd8contractordet25"
down_revision: Union[str, None] = "d4bc7stageresp24"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("contractors", sa.Column("details", sa.Text(), nullable=False, server_default=""))


def downgrade() -> None:
    op.drop_column("contractors", "details")
