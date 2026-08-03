"""delivery installation tracking (installed_at/installed_by)

Revision ID: c9ac2installed29
Revises: b8fa1geo28
"""
from __future__ import annotations
from typing import Union
import sqlalchemy as sa
from alembic import op

revision: str = "c9ac2installed29"
down_revision: Union[str, None] = "b8fa1geo28"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "deliveries", sa.Column("installed_at", sa.DateTime(timezone=True), nullable=True)
    )
    op.add_column(
        "deliveries",
        sa.Column("installed_by", sa.String(length=150), nullable=False, server_default=""),
    )


def downgrade() -> None:
    op.drop_column("deliveries", "installed_by")
    op.drop_column("deliveries", "installed_at")
