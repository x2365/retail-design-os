"""этап «Отгрузочные документы»: поля отгрузки в tasks

Revision ID: e3lm6shipdoc13
Revises: d2kf5notify12
Create Date: 2026-06-07
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

revision: str = "e3lm6shipdoc13"
down_revision: Union[str, None] = "d2kf5notify12"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    with op.batch_alter_table("tasks", schema=None) as b:
        b.add_column(sa.Column("shipment_order_no", sa.String(length=64), nullable=False, server_default=""))
        b.add_column(sa.Column("shipment_ship_date", sa.DateTime(timezone=True), nullable=True))
        b.add_column(sa.Column("shipment_acceptance_date", sa.DateTime(timezone=True), nullable=True))


def downgrade() -> None:
    with op.batch_alter_table("tasks", schema=None) as b:
        b.drop_column("shipment_acceptance_date")
        b.drop_column("shipment_ship_date")
        b.drop_column("shipment_order_no")
