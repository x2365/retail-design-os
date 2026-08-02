# Миграции (Alembic)

Схема версионируется через Alembic. URL базы берётся из `DATABASE_URL`
(те же настройки, что у приложения).

## Команды

Применить все миграции (создать/обновить схему):
```
cd backend
alembic upgrade head
```

Создать новую миграцию после изменения моделей (autogenerate):
```
alembic revision --autogenerate -m "что изменилось"
```

Откатить на одну ревизию назад:
```
alembic downgrade -1
```

Текущая ревизия БД / история:
```
alembic current
alembic history
```

## Дев vs прод

- **Локальная разработка (SQLite):** при старте приложения схема создаётся через
  `create_all()` — миграции запускать не обязательно, база пересоздаётся при
  удалении `retaildesign.db`.
- **Production (PostgreSQL):** `create_all()` не изменяет существующие таблицы,
  поэтому единственный безопасный путь — `alembic upgrade head` при деплое.

## Базовая ревизия

`0001_baseline_schema` — снимок текущей схемы (12 таблиц). Все последующие
изменения (TaskStage Enum, production_cost в копейках, task_stage_approvals,
task_stage_history, nomenclature_items, Delivery.region) добавляются отдельными
ревизиями поверх baseline.
