"""поля ТЗ задачи: артикул/размеры/упаковка/дата прихода на РЦ

Revision ID: b6rs9brief16
Revises: a5pq8paystat15
Create Date: 2026-06-08
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

revision: str = "b6rs9brief16"
down_revision: Union[str, None] = "a5pq8paystat15"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column("tasks", sa.Column("article", sa.String(length=80), nullable=False, server_default=""))
    op.add_column("tasks", sa.Column("dimensions", sa.String(length=120), nullable=False, server_default=""))
    op.add_column("tasks", sa.Column("packaging_primary", sa.String(length=160), nullable=False, server_default=""))
    op.add_column("tasks", sa.Column("packaging_secondary", sa.String(length=160), nullable=False, server_default=""))
    op.add_column("tasks", sa.Column("rc_arrival_date", sa.DateTime(timezone=True), nullable=True))


def downgrade() -> None:
    for col in ("rc_arrival_date", "packaging_secondary", "packaging_primary", "dimensions", "article"):
        op.drop_column("tasks", col)
