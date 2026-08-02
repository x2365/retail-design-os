"""CLI-запуск обхода напоминаний: `python -m app.reminders [--dry-run]`.

Предназначен для внешнего планировщика (cron/launchd). Безопасен к повторным
запускам — уведомления дедуплицируются по дню (см. services/reminders).
"""
from __future__ import annotations

import logging
import sys

from .database import SessionLocal
from .services import reminders


def main() -> None:
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s %(message)s")
    dry = "--dry-run" in sys.argv
    db = SessionLocal()
    try:
        result = reminders.run_reminders(db, dry_run=True if dry else None)
        print(f"reminders: создано={result['created']} разослано={result['dispatched']} "
              f"ошибок={result['failed']} dry_run={result['dry_run']}")
    finally:
        db.close()


if __name__ == "__main__":
    main()
