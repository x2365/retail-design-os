"""Точка сброса демо-данных.

Почему pg_dump/pg_restore, а не ручная построчная сериализация таблиц:
FK-порядок, sequence-счётчики автоинкремента, Enum/JSON-колонки — всё это
pg_dump уже умеет корректно, и это единственный по-настоящему проверенный
способ сделать consistent snapshot+restore всей схемы. Снепшот хранится как
бинарный blob в самой БД (DataSnapshot.payload), а не на диске веб-сервиса —
на Render free tier диск веб-сервиса стирается при каждом рестарте/деплое,
а строка в Postgres — нет.

data_snapshots и alembic_version намеренно исключены из дампа: иначе рестор
затирал бы сам себя (снепшот снепшота) и версию схемы.
"""

from __future__ import annotations

import datetime as dt
import os
import subprocess
import tempfile

from sqlalchemy.orm import Session

from ..config import get_settings
from ..models import DataSnapshot

EXCLUDED_TABLES = ["data_snapshots", "alembic_version"]
_DUMP_TIMEOUT_S = 120
_RESTORE_TIMEOUT_S = 180


def _require_postgres() -> str:
    settings = get_settings()
    if settings.is_sqlite:
        raise RuntimeError("Точка сброса поддерживается только для PostgreSQL")
    return settings.database_url


def take_snapshot(db: Session) -> DataSnapshot:
    """Дампит текущее состояние БД (кроме себя же) и сохраняет как новую
    единственную точку сброса — предыдущая (если была) удаляется."""
    database_url = _require_postgres()
    args = ["pg_dump", "--format=custom", "--no-owner", "--no-privileges"]
    for t in EXCLUDED_TABLES:
        args += ["--exclude-table", t]
    args += [database_url]
    result = subprocess.run(args, capture_output=True, timeout=_DUMP_TIMEOUT_S)
    if result.returncode != 0:
        raise RuntimeError(f"pg_dump failed: {result.stderr.decode(errors='replace')[:2000]}")
    payload = result.stdout
    db.query(DataSnapshot).delete()
    snap = DataSnapshot(
        taken_at=dt.datetime.now(dt.UTC), payload=payload, size_bytes=len(payload)
    )
    db.add(snap)
    db.commit()
    db.refresh(snap)
    return snap


def get_snapshot(db: Session) -> DataSnapshot | None:
    return db.query(DataSnapshot).order_by(DataSnapshot.id.desc()).first()


def restore_snapshot(db: Session) -> DataSnapshot:
    """Откатывает БД (кроме data_snapshots/alembic_version) к последней
    сохранённой точке сброса. Разрушительно и необратимо для всего, что
    накопилось после take_snapshot()."""
    database_url = _require_postgres()
    snap = get_snapshot(db)
    if snap is None:
        raise RuntimeError("Нет сохранённой точки сброса — сначала вызовите take_snapshot")

    with tempfile.NamedTemporaryFile(suffix=".dump", delete=False) as f:
        f.write(snap.payload)
        tmp_path = f.name
    try:
        args = [
            "pg_restore",
            "--clean",
            "--if-exists",
            "--no-owner",
            "--no-privileges",
            "--dbname",
            database_url,
            tmp_path,
        ]
        result = subprocess.run(args, capture_output=True, timeout=_RESTORE_TIMEOUT_S)
        if result.returncode != 0:
            stderr = result.stderr.decode(errors="replace")
            raise RuntimeError(f"pg_restore failed: {stderr[:2000]}")
    finally:
        os.unlink(tmp_path)
    return snap
