"""tasks.tirazh_qty (штуки в тираже, отдельно от tirazh_cost — стоимости)

Revision ID: b7d2tirazhqty33
Revises: f4b1renumber32
Create Date: 2026-08-10
"""

from __future__ import annotations

from typing import Union

import sqlalchemy as sa
from alembic import op

revision: str = "b7d2tirazhqty33"
down_revision: Union[str, None] = "f4b1renumber32"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "tasks", sa.Column("tirazh_qty", sa.Integer(), nullable=False, server_default="0")
    )


def downgrade() -> None:
    op.drop_column("tasks", "tirazh_qty")
