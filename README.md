# RetailDesign OS — система трекинга торгового оборудования

Бэкенд + фронтенд для отслеживания производства POSM (подставки, корнеры, дисплеи)
от ТЗ бренда до доставки в торговые точки (ТТ). Задачи проходят **12 этапов**
производственного пайплайна; система ведёт бюджеты по группам, оплаты подрядчикам,
согласования и доставку оборудования по сети магазинов.

## Стек

| Слой        | Технология                                                        |
|-------------|--------------------------------------------------------------------|
| API         | FastAPI + Pydantic v2 (авто-доки OpenAPI на `/docs`)               |
| ORM / БД    | SQLAlchemy 2.0; PostgreSQL (prod) / SQLite (dev)                   |
| Auth        | JWT (bearer), bcrypt, RBAC по ролям, rate limiting на login         |
| Сервер      | Gunicorn + Uvicorn-воркеры                                          |
| Фронт       | React 18 + TypeScript + Vite, TanStack Query, типы из OpenAPI-схемы |
| Оркестрация | Docker Compose (db + api + frontend), nginx отдаёт SPA + проксирует `/api` |
| CI          | GitHub Actions — ruff/mypy/pytest (backend), eslint/tsc/build (frontend) |

## Быстрый старт

### Вариант 1 — Docker (как в проде: Postgres + воркеры + nginx)
```bash
JWT_SECRET=$(openssl rand -hex 32) docker compose up --build
# открыть http://localhost:8080
```
Горизонтальное масштабирование: `docker compose up --build --scale api=3`.

### Вариант 2 — локально без Docker (SQLite, ноль настройки)
```bash
cd backend
pip install -r requirements.txt
uvicorn app.main:app --reload          # API на :8000, доки на :8000/docs

# в другом терминале — фронт (Vite dev-сервер, hot reload):
cd ../frontend
npm install
npm run dev                            # http://localhost:5500
```
Vite-сервер проксирует `/api/*` на `http://localhost:8000` (см. `vite.config.ts`),
так что фронт всегда обращается к бэкенду через тот же origin, что и в проде за nginx.

### Демо-доступы
Сидируются при первом старте (пароль = `<роль>123`):

| Email                | Роль       | Права                                  |
|----------------------|------------|----------------------------------------|
| admin@retail.os      | admin      | всё                                    |
| manager@retail.os    | manager    | задачи (CRUD), доставки, согласования   |
| brand@retail.os      | brand      | просмотр + согласования                 |
| retailer@retail.os   | retailer   | просмотр + подтверждение доставок в ТТ  |
| viewer@retail.os     | viewer     | только чтение                           |

## Модель данных

```
Group ──< Brand ──< Task ──< Delivery >── RetailPoint
                     │  └─< Approval
                     │  └── Payment (1:1)
                     └──< TeamMember (M:N)
User(role)           # аутентификация и RBAC
```

Ключевые решения для масштабируемости:
- **Stateless API** — любое число воркеров/реплик за балансировщиком; состояние только в БД.
- **Производные значения не хранятся**: `days_left`, прогресс этапа и счётчики ТТ
  (`tt_total/ok/partial/miss`) вычисляются на лету. Счётчики ТТ — это агрегаты
  по таблице `deliveries`, считаются одним групповым запросом (без N+1).
- **Списки пагинируются** и фильтруются на стороне БД; индексы на FK, `stage`,
  `deadline`, `status`.
- KPI считаются агрегатными SQL-запросами, а не вытягиванием всех строк.

## Аутентификация

`POST /api/auth/login` (form-urlencoded `username`+`password`) → `{access_token, user}`.
Дальше каждый запрос с заголовком `Authorization: Bearer <token>`.
Все `/api/*` требуют токен (кроме `/auth/login` и `/dashboard/meta`).

## Основные эндпоинты

| Метод/путь                          | Доступ            | Назначение                       |
|-------------------------------------|-------------------|----------------------------------|
| `POST /api/auth/login`              | —                 | вход, выдать JWT                 |
| `GET  /api/auth/me`                 | любой             | текущий пользователь             |
| `GET  /api/dashboard/kpis`          | любой             | KPI дашборда                     |
| `GET  /api/groups` `/brands`        | любой             | справочники                      |
| `GET  /api/tasks`                   | любой             | список задач (фильтры+пагинация) |
| `GET  /api/tasks/{code}`            | любой             | карточка задачи                  |
| `POST /api/tasks`                   | manager, admin    | создать задачу (ТЗ)              |
| `PATCH /api/tasks/{code}`           | manager, admin    | обновить (этап, сроки, бюджет)   |
| `GET  /api/tasks/{code}/deliveries` | любой             | доставки задачи по точкам        |
| `GET  /api/retail-points`           | любой             | каталог ТТ                       |
| `PATCH /api/deliveries/{id}`        | retailer, manager | подтвердить доставку в ТТ        |
| `GET  /api/approvals`               | любой             | очередь согласований             |
| `POST /api/approvals/{id}/approve`  | brand, retailer, manager | согласовать               |
| `GET  /api/payments` `/api/tt`      | любой             | оплаты / сводка по ТТ            |

Фильтры списка задач: `?group=A&band=logistics&urgent=true&due_within=14&search=...&page=1&page_size=50`.
`band` ∈ `dev | approval | production | logistics` (соответствует колонкам канбана).

## Тесты
```bash
cd backend && pip install -r requirements-dev.txt
cd backend && pytest -q              # auth, RBAC, состояние пайплайна, документы, KPI
ruff check backend && mypy backend/app   # lint + типы
```
Каждый тест изолирован: справочные данные (пользователи/группы/бренды/ТТ) сидируются
один раз на сессию, а любые изменения, которые делает тест, откатываются в конце
(SAVEPOINT-транзакция) — без пересидирования 90 точек перед каждым тестом.

## Переход на продакшен
- Задать сильный `JWT_SECRET` и `DATABASE_URL` на Postgres.
- `CORS_ORIGINS` — список доменов фронта (не `*`).
- Заменить `Base.metadata.create_all` на миграции **Alembic**.
- Фронт раздавать через CDN/nginx; API — за load balancer, N реплик.
