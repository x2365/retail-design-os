"""поля этапа «Образец и Производство»

Revision ID: e9wx2sampleprod19
Revises: d8vw1kpcontr18
Create Date: 2026-06-08
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

revision: str = "e9wx2sampleprod19"
down_revision: Union[str, None] = "d8vw1kpcontr18"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column("tasks", sa.Column("sample_status", sa.String(length=16), nullable=False, server_default="unpaid"))
    op.add_column("tasks", sa.Column("sample_deadline", sa.DateTime(timezone=True), nullable=True))
    op.add_column("tasks", sa.Column("sample_approved_by", sa.String(length=150), nullable=False, server_default=""))
    op.add_column("tasks", sa.Column("sample_approved_at", sa.DateTime(timezone=True), nullable=True))
    op.add_column("tasks", sa.Column("production_end_date", sa.DateTime(timezone=True), nullable=True))


def downgrade() -> None:
    for col in ("production_end_date", "sample_approved_at", "sample_approved_by",
                "sample_deadline", "sample_status"):
        op.drop_column("tasks", col)
