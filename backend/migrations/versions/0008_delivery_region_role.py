"""П4: deliveries.region + расширение users.role (shipment_manager)

Revision ID: f8gb1region08
Revises: e7fa9appr007
Create Date: 2026-06-05
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

revision: str = "f8gb1region08"
down_revision: Union[str, None] = "e7fa9appr007"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    with op.batch_alter_table("deliveries", schema=None) as b:
        b.add_column(sa.Column("region", sa.String(length=16), nullable=False, server_default="local"))
        b.create_index("ix_deliveries_region", ["region"])
    # роль может стать длиннее ('shipment_manager') — расширяем колонку для PG
    with op.batch_alter_table("users", schema=None) as b:
        b.alter_column("role", existing_type=sa.String(length=8), type_=sa.String(length=20),
                       existing_nullable=False)


def downgrade() -> None:
    with op.batch_alter_table("users", schema=None) as b:
        b.alter_column("role", existing_type=sa.String(length=20), type_=sa.String(length=8),
                       existing_nullable=False)
    with op.batch_alter_table("deliveries", schema=None) as b:
        b.drop_index("ix_deliveries_region")
        b.drop_column("region")
