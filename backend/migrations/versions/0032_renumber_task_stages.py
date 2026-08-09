"""renumber the 12-stage TaskStage pipeline down to 10 stages

Old stage 4 "SUMMARY" (no gate) is folded into stage 3 "Согласования" as a
tab; old stages 8 "Готов к отгрузке" and 9 "Доставка" (both no gate) are
merged into one stage "Отгрузка". Everything else shifts down to fill the
gaps. See backend/app/models/enums.py TaskStage for the new scheme.

old->new map: {1:1, 2:2, 3:3, 4:3, 5:4, 6:5, 7:6, 8:7, 9:7, 10:8, 11:9, 12:10}

Touches 4 tables that carry raw stage-number integers: tasks.stage,
task_stage_history.from_stage/to_stage, documents.stage (which tab an
uploaded file belongs to — must move together with the frontend's tab
renumbering or old files become invisible), task_stage_approvals.stage
(has a UNIQUE(task_id, stage) constraint — a task with rows on both members
of a merge pair, e.g. old 3 and 4, would violate it on a naive UPDATE, so
those are de-duplicated first, keeping whichever row already sits on the
merge target).

Row-remap order is safety-critical, not arbitrary:
- upgrade() processes old values ASCENDING (1..12). The map only ever holds
  or lowers a value (new_i <= i for every i), so by induction any row a
  step touches has already been moved below the bucket the next ascending
  step reads — no cross-contamination. Processing DESCENDING would corrupt
  data: e.g. old-10 (Монтаж) would move into bucket 8, and the very next
  step (old-8 -> 7) would then sweep those just-relocated rows up together
  with real old-8 rows, silently merging Монтаж into Отгрузка.
- downgrade() mirrors this in reverse: DESCENDING new values (10..1), for
  the same reason applied backwards (old_i >= i for the reverse map).

downgrade() is inherently lossy at the two merge points and picks a
documented default rather than guessing: new-3 -> old-3 (SUMMARY was a pure
pass-through with no state of its own to lose), new-7 -> old-8 (arbitrary
but documented; downgrade is a break-glass path, not a normal code path).

Revision ID: f4b1renumber32
Revises: e2ce4arrival31
Create Date: 2026-08-10
"""

from __future__ import annotations

from typing import Union

import sqlalchemy as sa
from alembic import op

revision: str = "f4b1renumber32"
down_revision: Union[str, None] = "e2ce4arrival31"
branch_labels = None
depends_on = None

_FORWARD = {1: 1, 2: 2, 3: 3, 4: 3, 5: 4, 6: 5, 7: 6, 8: 7, 9: 7, 10: 8, 11: 9, 12: 10}
_BACKWARD = {10: 12, 9: 11, 8: 10, 7: 8, 6: 7, 5: 6, 4: 5, 3: 3, 2: 2, 1: 1}

_PLAIN_COLUMNS = [
    ("tasks", "stage"),
    ("task_stage_history", "from_stage"),
    ("task_stage_history", "to_stage"),
    ("documents", "stage"),
]


def _remap_plain(bind, mapping: dict[int, int], order: list[int]) -> None:
    for old in order:
        new = mapping[old]
        if new == old:
            continue
        for table, col in _PLAIN_COLUMNS:
            bind.execute(
                sa.text(f"UPDATE {table} SET {col} = :new WHERE {col} = :old"),
                {"new": new, "old": old},
            )


def _remap_approvals(bind, mapping: dict[int, int], order: list[int]) -> None:
    for old in order:
        new = mapping[old]
        if new == old:
            continue
        # A task with approval rows on BOTH `old` and `new` would violate
        # UNIQUE(task_id, stage) on a plain UPDATE — drop the mover, keep
        # whichever row already sits on the merge target.
        dupes = bind.execute(
            sa.text(
                "SELECT a.id FROM task_stage_approvals a "
                "JOIN task_stage_approvals b ON a.task_id = b.task_id "
                "WHERE a.stage = :old AND b.stage = :new"
            ),
            {"old": old, "new": new},
        ).fetchall()
        for (row_id,) in dupes:
            bind.execute(sa.text("DELETE FROM task_stage_approvals WHERE id = :id"), {"id": row_id})
        bind.execute(
            sa.text("UPDATE task_stage_approvals SET stage = :new WHERE stage = :old"),
            {"new": new, "old": old},
        )


def upgrade() -> None:
    bind = op.get_bind()
    order = sorted(_FORWARD)  # ascending 1..12 — see module docstring
    _remap_plain(bind, _FORWARD, order)
    _remap_approvals(bind, _FORWARD, order)
    with op.batch_alter_table("tasks", schema=None) as b:
        b.drop_constraint("ck_tasks_stage_range", type_="check")
        b.create_check_constraint("ck_tasks_stage_range", "stage >= 1 AND stage <= 10")


def downgrade() -> None:
    with op.batch_alter_table("tasks", schema=None) as b:
        b.drop_constraint("ck_tasks_stage_range", type_="check")
        b.create_check_constraint("ck_tasks_stage_range", "stage >= 1 AND stage <= 12")
    bind = op.get_bind()
    order = sorted(_BACKWARD, reverse=True)  # descending 10..1 — see module docstring
    _remap_plain(bind, _BACKWARD, order)
    _remap_approvals(bind, _BACKWARD, order)
