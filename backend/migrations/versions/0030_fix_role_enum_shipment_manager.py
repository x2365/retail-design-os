"""fix: actually widen the Postgres role enum to include shipment_manager

Revision ID: d1bd3roleenum30
Revises: c9ac2installed29

Migration 0008 (f8gb1region08) tried to make room for the longer
'shipment_manager' role value by widening `users.role` as if it were a plain
VARCHAR — but on Postgres, SQLAlchemy's `Enum(Role)` column is a *native*
Postgres ENUM type, not a VARCHAR, so that ALTER was a silent no-op: it never
errored, but the underlying enum type's allowed values were never extended.
Invisible until now because local/test dev runs on SQLite, where enums are
just VARCHAR + CHECK, and the deployed database was bootstrapped via
`create_all()` (which builds the enum fresh from the current model, values
included) rather than by replaying this migration.

`ADD VALUE IF NOT EXISTS` is idempotent — safe to run whether or not a given
database already has the value (e.g. one created via create_all does).
"""
from __future__ import annotations
from typing import Union
from alembic import op

revision: str = "d1bd3roleenum30"
down_revision: Union[str, None] = "c9ac2installed29"
branch_labels = None
depends_on = None


def upgrade() -> None:
    bind = op.get_bind()
    if bind.dialect.name == "postgresql":
        # ALTER TYPE ... ADD VALUE cannot run inside the same transaction
        # that then uses the new value, but running it alone (Postgres 12+)
        # inside alembic's per-migration transaction is fine.
        op.execute("ALTER TYPE role ADD VALUE IF NOT EXISTS 'shipment_manager'")
    # SQLite has no real enum type (Role is stored as VARCHAR there) — nothing to do.


def downgrade() -> None:
    # Postgres has no ALTER TYPE ... DROP VALUE; removing an enum value
    # safely requires rebuilding the type, not worth it for a downgrade path.
    pass
