"""production_cost + перевод денег в копейки

Добавляет tasks.production_cost (копейки) и переводит все целочисленные денежные
поля из «целых единиц валюты» в копейки (×100):
  tasks: production_cost(=budget), budget, sample_cost, tirazh_cost, prepaid
  groups: budget_planned, budget_spent
  equipment: est_budget, est_sample, est_tirazh
(payments.* — строковые, не трогаем.)

Revision ID: a1c3f0money03
Revises: 33db2d23c22f
Create Date: 2026-06-05
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

revision: str = "a1c3f0money03"
down_revision: Union[str, None] = "33db2d23c22f"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    with op.batch_alter_table("tasks", schema=None) as b:
        b.add_column(sa.Column("production_cost", sa.Integer(), nullable=False, server_default="0"))

    # production_cost берётся из текущего (рублёвого) budget ДО умножения,
    # затем все суммы переводятся в копейки.
    op.execute("UPDATE tasks SET production_cost = budget * 100")
    op.execute(
        "UPDATE tasks SET budget = budget * 100, sample_cost = sample_cost * 100, "
        "tirazh_cost = tirazh_cost * 100, prepaid = prepaid * 100"
    )
    op.execute("UPDATE groups SET budget_planned = budget_planned * 100, budget_spent = budget_spent * 100")
    op.execute("UPDATE equipment SET est_budget = est_budget * 100, est_sample = est_sample * 100, est_tirazh = est_tirazh * 100")


def downgrade() -> None:
    op.execute(
        "UPDATE tasks SET budget = budget / 100, sample_cost = sample_cost / 100, "
        "tirazh_cost = tirazh_cost / 100, prepaid = prepaid / 100"
    )
    op.execute("UPDATE groups SET budget_planned = budget_planned / 100, budget_spent = budget_spent / 100")
    op.execute("UPDATE equipment SET est_budget = est_budget / 100, est_sample = est_sample / 100, est_tirazh = est_tirazh / 100")
    with op.batch_alter_table("tasks", schema=None) as b:
        b.drop_column("production_cost")
