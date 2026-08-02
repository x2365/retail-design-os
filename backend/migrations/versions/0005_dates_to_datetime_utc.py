"""даты -> datetime (UTC)

Переводит tasks.deadline_tt, tasks.launch_date, payments.kp_date с DATE на
DATETIME (timezone-aware, хранится в UTC). Инвариант: все даты/время — UTC.

Для SQLite значения DATE хранятся как 'YYYY-MM-DD'; после смены типа дописываем
время, чтобы строки парсились как datetime. Для PostgreSQL date->timestamptz
кастуется штатно.

Revision ID: c5da7e0utc05
Revises: b2d4lib0004
Create Date: 2026-06-05
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

revision: str = "c5da7e0utc05"
down_revision: Union[str, None] = "b2d4lib0004"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

_COLS = [("tasks", "deadline_tt"), ("tasks", "launch_date"), ("payments", "kp_date")]


def upgrade() -> None:
    bind = op.get_bind()
    if bind.dialect.name == "sqlite":
        # SQLite динамически типизирован; смена типа через alembic делает
        # CAST(... AS DATETIME) → NUMERIC-аффинити портит дату ('2026-09-15' → 2026).
        # Поэтому просто нормализуем текст в формат datetime — ORM читает значение
        # по типу из модели (DateTime), независимо от объявленного типа колонки.
        for tbl, col in _COLS:
            op.execute(
                f"UPDATE {tbl} SET {col} = {col} || ' 00:00:00.000000' "
                f"WHERE {col} IS NOT NULL AND length({col}) = 10"
            )
        return
    for tbl, col in _COLS:
        with op.batch_alter_table(tbl, schema=None) as b:
            b.alter_column(
                col,
                existing_type=sa.Date(),
                type_=sa.DateTime(timezone=True),
                existing_nullable=True,
                postgresql_using=f"{col}::timestamptz",
            )


def downgrade() -> None:
    bind = op.get_bind()
    if bind.dialect.name == "sqlite":
        for tbl, col in _COLS:
            op.execute(
                f"UPDATE {tbl} SET {col} = substr({col}, 1, 10) "
                f"WHERE {col} IS NOT NULL AND length({col}) > 10"
            )
        return
    for tbl, col in _COLS:
        with op.batch_alter_table(tbl, schema=None) as b:
            b.alter_column(
                col,
                existing_type=sa.DateTime(timezone=True),
                type_=sa.Date(),
                existing_nullable=True,
                postgresql_using=f"{col}::date",
            )
