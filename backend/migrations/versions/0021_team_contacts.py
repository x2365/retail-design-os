"""контакты участников: email + telegram

Revision ID: a1yz4teamcontact21
Revises: f0xy3briefjson20
Create Date: 2026-06-09
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

revision: str = "a1yz4teamcontact21"
down_revision: Union[str, None] = "f0xy3briefjson20"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column("team_members", sa.Column("email", sa.String(length=160), nullable=False, server_default=""))
    op.add_column("team_members", sa.Column("telegram", sa.String(length=80), nullable=False, server_default=""))


def downgrade() -> None:
    op.drop_column("team_members", "telegram")
    op.drop_column("team_members", "email")
