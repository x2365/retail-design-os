"""П8: equipment.rc_ship_date/rc_remainder + расширение documents.kind

Revision ID: a9hc2rcfields09
Revises: f8gb1region08
Create Date: 2026-06-05
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

revision: str = "a9hc2rcfields09"
down_revision: Union[str, None] = "f8gb1region08"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    with op.batch_alter_table("equipment", schema=None) as b:
        b.add_column(sa.Column("rc_ship_date", sa.DateTime(timezone=True), nullable=True))
        b.add_column(sa.Column("rc_remainder", sa.Integer(), nullable=False, server_default="0"))
    # новые значения DocKind ('nomenclature' и т.д.) длиннее — расширяем колонку
    with op.batch_alter_table("documents", schema=None) as b:
        b.alter_column("kind", existing_type=sa.String(length=7), type_=sa.String(length=16),
                       existing_nullable=False)


def downgrade() -> None:
    with op.batch_alter_table("documents", schema=None) as b:
        b.alter_column("kind", existing_type=sa.String(length=16), type_=sa.String(length=7),
                       existing_nullable=False)
    with op.batch_alter_table("equipment", schema=None) as b:
        b.drop_column("rc_remainder")
        b.drop_column("rc_ship_date")
