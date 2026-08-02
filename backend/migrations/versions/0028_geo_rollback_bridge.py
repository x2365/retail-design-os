"""geo rollback bridge (no-op)

Revision ID: b8fa1geo28
Revises: a7ef0samplegates27

Историческая миграция «geo reference» (страны/юрлица/retail_points.country_id)
была откатана вместе с режимом проектирования 3-х стран. Сам файл миграции
удалён, но базы, которые успели её применить, остались «проштампованы» на
revision id ``b8fa1geo28``. Без этого ревизия не находится и
``alembic upgrade head`` падает с ошибкой "Can't locate revision".

Эта no-op миграция восстанавливает только идентификатор ревизии (мост),
чтобы такие базы могли догнать head без пересоздания (--fresh) и потери
данных. Никаких изменений схемы она не вносит: гео-таблиц в моделях больше
нет, а возможные «осиротевшие» таблицы в старых БД безвредны (модели их
игнорируют). Для чистой схемы при желании используйте --fresh.
"""
from __future__ import annotations

# revision identifiers, used by Alembic.
revision = "b8fa1geo28"
down_revision = "a7ef0samplegates27"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # no-op: гео-функциональность откатана, схему не трогаем
    pass


def downgrade() -> None:
    # no-op
    pass
