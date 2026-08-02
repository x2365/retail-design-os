"""sample received + 3 approval gates (qc/brand/network)

Revision ID: a7ef0samplegates27
Revises: f6de9kpnetwork26
"""
from __future__ import annotations
from typing import Union
import sqlalchemy as sa
from alembic import op

revision: str = "a7ef0samplegates27"
down_revision: Union[str, None] = "f6de9kpnetwork26"
branch_labels = None
depends_on = None

_COLS = [
    ("sample_received", sa.Boolean(), False, "0"),
    ("sample_received_date", sa.DateTime(timezone=True), True, None),
    ("sample_qc_approved_by", sa.String(length=150), False, ""),
    ("sample_qc_approved_at", sa.DateTime(timezone=True), True, None),
    ("sample_brand_approved_by", sa.String(length=150), False, ""),
    ("sample_brand_approved_at", sa.DateTime(timezone=True), True, None),
    ("sample_network_approved_by", sa.String(length=150), False, ""),
    ("sample_network_approved_at", sa.DateTime(timezone=True), True, None),
]


def upgrade() -> None:
    for name, typ, nullable, default in _COLS:
        kw = {}
        if default is not None:
            kw["server_default"] = default
        op.add_column("tasks", sa.Column(name, typ, nullable=nullable, **kw))


def downgrade() -> None:
    for name, *_ in reversed(_COLS):
        op.drop_column("tasks", name)
