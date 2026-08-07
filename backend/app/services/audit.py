"""Shared helper for writing to the audit_log — every deletion across the
app (task/brand/equipment/retail point/document/nomenclature) records who
deleted what and when, same table/UI already used for budget-field edits."""

from __future__ import annotations

from sqlalchemy.orm import Session

from .. import models


def log_deletion(
    db: Session, user: models.User, *, entity_type: str, entity_code: str, description: str
) -> None:
    # old_value/entity_code are String(120)/String(32) on Postgres — an
    # unenforced length in SQLite (local/tests) but a hard error in prod.
    db.add(
        models.AuditLog(
            user_id=user.id,
            user_name=user.full_name,
            entity_type=entity_type,
            entity_code=entity_code[:32],
            field="Удаление",
            old_value=description[:120],
            new_value="—",
        )
    )
