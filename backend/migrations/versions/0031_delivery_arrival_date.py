"""delivery arrival_date (дата прихода в ТТ, вручную)

Revision ID: e2ce4arrival31
Revises: d1bd3roleenum30
"""
from __future__ import annotations
from typing import Union
import sqlalchemy as sa
from alembic import op

revision: str = "e2ce4arrival31"
down_revision: Union[str, None] = "d1bd3roleenum30"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("deliveries", sa.Column("arrival_date", sa.Date(), nullable=True))


def downgrade() -> None:
    op.drop_column("deliveries", "arrival_date")
