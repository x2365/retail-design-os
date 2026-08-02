"""справочник подрядчиков + поля этапа «КП»

Revision ID: d8vw1kpcontr18
Revises: c7tu0prepcom17
Create Date: 2026-06-08
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

revision: str = "d8vw1kpcontr18"
down_revision: Union[str, None] = "c7tu0prepcom17"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "contractors",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("name", sa.String(length=160), nullable=False),
        sa.Column("contact", sa.String(length=200), nullable=False, server_default=""),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default="1"),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
    )
    op.create_index("ix_contractors_name", "contractors", ["name"], unique=True)
    op.add_column("tasks", sa.Column("kp_contractor", sa.String(length=160), nullable=False, server_default=""))
    op.add_column("tasks", sa.Column("kp_manager_approved_by", sa.String(length=150), nullable=False, server_default=""))
    op.add_column("tasks", sa.Column("kp_manager_approved_at", sa.DateTime(timezone=True), nullable=True))
    op.add_column("tasks", sa.Column("kp_director_approved_by", sa.String(length=150), nullable=False, server_default=""))
    op.add_column("tasks", sa.Column("kp_director_approved_at", sa.DateTime(timezone=True), nullable=True))


def downgrade() -> None:
    for col in ("kp_director_approved_at", "kp_director_approved_by", "kp_manager_approved_at",
                "kp_manager_approved_by", "kp_contractor"):
        op.drop_column("tasks", col)
    op.drop_index("ix_contractors_name", table_name="contractors")
    op.drop_table("contractors")
