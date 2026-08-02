# Архитектура базы данных — RetailDesign OS

Система трекинга производства торгового оборудования (POSM): задачи проходят
12-этапный производственный конвейер от ТЗ бренда до доставки в торговые точки.

- **СУБД:** PostgreSQL (production) / SQLite (локальная разработка).
- **ORM:** SQLAlchemy 2.0 (декларативные модели, `Mapped[...]`).
- **Кодировка:** UTF-8. **Часовой пояс:** все отметки времени в UTC (`timestamptz`).
- **Деньги:** целочисленные поля — в **копейках** (валюта — в `currency`). Канонический
  показатель стоимости задачи — `tasks.production_cost`; `budget/sample_cost/tirazh_cost/prepaid`
  — детализация. `payments.*` — строковые (исторические значения «как в КП»).

> Назначение документа — зафиксировать актуальную схему: таблицы, типы, связи,
> индексы, ограничения и принципы. Источник истины — `backend/app/models/` (пакет).

---

## 1. ER-диаграмма

```mermaid
erDiagram
    GROUPS        ||--o{ BRANDS        : "содержит"
    BRANDS        ||--o{ TASKS         : "владеет"
    BRANDS        ||--o{ EQUIPMENT     : "имеет в библиотеке"
    EQUIPMENT     |o--o{ TASKS         : "запущено в производство как"
    TASKS         ||--o{ DELIVERIES    : "отгружается"
    RETAIL_POINTS ||--o{ DELIVERIES    : "получает"
    TASKS         ||--o{ APPROVALS     : "требует согласований"
    TASKS         ||--|| PAYMENTS      : "имеет оплату"
    TASKS         ||--o{ DOCUMENTS     : "содержит файлы"
    TASKS         }o--o{ TEAM_MEMBERS  : "команда (task_members)"
    USERS         ||--o{ DOCUMENTS     : "загрузил"

    GROUPS {
        int    id PK
        string code UK "A/B/C"
        string name
        string color
        int    budget_planned
        int    budget_spent
    }
    BRANDS {
        int    id PK
        string name UK
        int    group_id FK
    }
    EQUIPMENT {
        int    id PK
        int    brand_id FK
        string name
        string kind
        int    est_budget
        bool   is_active
        int    times_produced
    }
    TASKS {
        int    id PK
        string code UK "RD-041"
        string name
        int    brand_id FK
        int    equipment_id FK "nullable"
        int    stage "1..12"
        bool   urgent

        datetime deadline_tt
        datetime launch_date
        string currency
        int    budget
        int    sample_cost
        int    tirazh_cost
        int    prepaid
    }
    RETAIL_POINTS {
        int    id PK
        string code UK "TT-001"
        string name
        string city
        string address
    }
    DELIVERIES {
        int      id PK
        int      task_id FK
        int      retail_point_id FK
        enum     status
        int      qty_expected
        int      qty_received
        datetime confirmed_at
        string   note
    }
    APPROVALS {
        int    id PK
        int    task_id FK "nullable"
        string from_name
        string type
        enum   status
    }
    PAYMENTS {
        int    id PK
        int    task_id FK UK
        string contractor
        datetime kp_date
        string status
    }
    DOCUMENTS {
        int    id PK
        int    task_id FK
        enum   kind
        int    stage "nullable, 1..12"
        string filename
        string storage_name
        int    uploaded_by_id FK "nullable"
    }
    TEAM_MEMBERS {
        int    id PK
        string name UK
        string role
    }
    USERS {
        int    id PK
        string email UK
        string full_name
        string hashed_password
        enum   role
        bool   is_active
    }
```

---

## 2. Перечисления (enum)

| Enum | Значения | Где используется |
|------|----------|------------------|
| `Role` | `admin`, `manager`, `brand`, `retailer`, `shipment_manager`, `viewer` | `users.role` — управление доступом (RBAC) |
| `ApprovalStatus` | `pending`, `approved`, `rejected` | `approvals.status` |
| `DeliveryStatus` | `pending`, `delivered`, `partial`, `missing` | `deliveries.status` |
| `ShipmentRegion` | `local`, `rc`, `cis`, `middle_east` | `deliveries.region` (П4) |
| `DocKind` | `brief`, `kp`, `sketch`, `model3d`, `photo`, `nomenclature`, `layout`, `ds`, `invoice`, `waybill`, `registry`, `planogram`, `other` | `documents.kind` |
| `NomenclatureStatus` | `draft`, `sent_to_rc`, `registered` | `nomenclature_items.status` (П3) |
| `TaskStage` (IntEnum 1..12) | `BRIEF_RECEIVED`…`CLOSED` (см. ниже) | `tasks.stage` (тип-безопасность в коде; в БД хранится `int` 1..12 + CHECK) |

**Тип оборудования** (`equipment.kind`) хранится строкой из набора:
`display`, `stand`, `corner`, `shelf`, `container`, `other` (валидируется на уровне API).

**Конвейер этапов** (`tasks.stage` = `TaskStage`, значения 1..12):
1. `BRIEF_RECEIVED` — ТЗ получено · 2. `SKETCH` — Эскизирование ·
3. `DESIGN_APPROVAL` — Согласование дизайна · 4. `PRE_PRODUCTION` — Подготовка к производству ·
5. `PRODUCTION` — Производство · 6. `QUALITY_CONTROL` — Контроль качества ·
7. `PACKING` — Упаковка · 8. `READY_FOR_DELIVERY` — Готов к отгрузке ·
9. `DELIVERY` — Доставка · 10. `INSTALLATION` — Монтаж ·
11. `FINAL_APPROVAL` — Финальное согласование · 12. `CLOSED` — Закрыт.

Закупочная специфика (КП, образец, ШК/номенклатура, регионы отгрузки) реализуется
**под-статусами/полями внутри** этих этапов (гибридная модель, Вариант В).

**Переходы** (`app/services/task_stage.py`): вперёд только на `+1` (перескок запрещён),
возврат на любой предыдущий этап разрешён; `CLOSED` — по предусловиям (все
`Deliveries=DELIVERED` + есть `Payment` + все обязательные `Approvals`).

---

## 3. Общие соглашения

- **Первичные ключи** — суррогатные `id INTEGER` (autoincrement / `BIGSERIAL` в Postgres).
- **Бизнес-ключи** — человекочитаемые коды с уникальным индексом: `tasks.code` (`RD-041`),
  `retail_points.code` (`TT-001`), `groups.code` (`A/B/C`), `brands.name`, `users.email`.
- **Отметки времени** — миксин `TimestampMixin` добавляет `created_at` и `updated_at`
  (`timestamptz`, server-default `now()`, `updated_at` обновляется при UPDATE).
- **Поведение при удалении (ON DELETE):**
  - `RESTRICT` — нельзя удалить родителя при наличии детей (`groups←brands`, `brands←tasks`, `retail_points←deliveries`).
  - `CASCADE` — дети удаляются вместе с родителем (`tasks←deliveries/documents/task_members`, `brands←equipment`).
  - `SET NULL` — ссылка обнуляется (`equipment←tasks.equipment_id`, `users←documents.uploaded_by_id`, `tasks←approvals.task_id`).

---

## 4. Таблицы

### 4.1 `users` — пользователи и роли
| Колонка | Тип | Ограничения / индекс | Примечание |
|---|---|---|---|
| id | int | PK | |
| email | varchar(160) | UNIQUE, index | логин |
| full_name | varchar(160) | | |
| hashed_password | varchar(255) | | bcrypt-хэш |
| role | enum(Role) | index, default `viewer` | RBAC |
| is_active | bool | default `true` | блокировка доступа |
| created_at / updated_at | timestamptz | | |

### 4.2 `groups` — бюджетные группы
| Колонка | Тип | Ограничения | Примечание |
|---|---|---|---|
| id | int | PK | |
| code | varchar(8) | UNIQUE, index | `A` / `B` / `C` |
| name | varchar(120) | | |
| color | varchar(16) | | hex для UI |
| budget_planned | int | default 0 | план бюджета |
| budget_spent | int | default 0 | факт (план — позже из 1С) |

### 4.3 `brands` — бренды
| Колонка | Тип | Ограничения | Примечание |
|---|---|---|---|
| id | int | PK | |
| name | varchar(120) | UNIQUE, index | |
| group_id | int | FK→groups.id (RESTRICT), index | |

### 4.4 `team_members` — участники команд
| Колонка | Тип | Ограничения |
|---|---|---|
| id | int | PK |
| name | varchar(120) | UNIQUE, index |
| role | varchar(80) | default «Менеджер» |

### 4.5 `retail_points` — каталог торговых точек (ТТ)
| Колонка | Тип | Ограничения | Примечание |
|---|---|---|---|
| id | int | PK | |
| code | varchar(16) | UNIQUE, index | `TT-001` |
| name | varchar(160) | | |
| city | varchar(80) | index, default '' | |
| address | varchar(200) | default '' | |

### 4.6 `equipment` — библиотека оборудования
| Колонка | Тип | Ограничения | Примечание |
|---|---|---|---|
| id | int | PK | |
| brand_id | int | FK→brands.id (CASCADE), index | |
| name | varchar(200) | | |
| kind | varchar(40) | default `other` | тип изделия |
| description | varchar(500) | default '' | |
| dimensions | varchar(80) | default '' | «45×45×120 мм» |
| currency | varchar(8) | default `RUB` | |
| est_budget / est_sample / est_tirazh | int | default 0, ≥ 0 (API) | плановые суммы |
| is_active | bool | default `true` | «используется / в архиве» |
| times_produced | int | default 0 | счётчик запусков в производство |

### 4.7 `tasks` — производственные задачи (ядро)
| Колонка | Тип | Ограничения | Примечание |
|---|---|---|---|
| id | int | PK | |
| code | varchar(16) | UNIQUE, index | `RD-041` |
| name | varchar(200) | | |
| brand_id | int | FK→brands.id (RESTRICT), index | |
| equipment_id | int | FK→equipment.id (SET NULL), nullable, index | из какого изделия запущена |
| stage | int | index, default 1, **CHECK 1..12** | `TaskStage` (IntEnum) в коде; переходы — через `services/task_stage.py` |
| urgent | bool | default `false` | |
| deadline_tt | datetime (UTC) | nullable, index | дедлайн наличия в ТТ |
| launch_date | datetime (UTC) | nullable | дата лонча продукта |
| currency | varchar(8) | default `RUB` | валюта расчётов |
| production_cost | int | default 0, ≥ 0 | **канонический показатель стоимости (копейки)** — источник для KPI бренда |
| budget / sample_cost / tirazh_cost / prepaid | int | default 0, ≥ 0 (API) | финансы-детализация (**копейки**) |

Индексы: `code` (UK), `brand_id`, `equipment_id`, `stage`, `deadline_tt`.

### 4.8 `task_members` — связь задача↔участник (M:N)
| Колонка | Тип | Ограничения |
|---|---|---|
| task_id | int | PK, FK→tasks.id (CASCADE) |
| member_id | int | PK, FK→team_members.id (CASCADE) |

Составной первичный ключ `(task_id, member_id)`.

### 4.9 `deliveries` — отгрузки в точки (нормализованный ТТ-трекинг)
| Колонка | Тип | Ограничения | Примечание |
|---|---|---|---|
| id | int | PK | |
| task_id | int | FK→tasks.id (CASCADE), index | |
| retail_point_id | int | FK→retail_points.id (RESTRICT), index | |
| status | enum(DeliveryStatus) | index, default `pending` | |
| qty_expected | int | default 0 | |
| qty_received | int | default 0, ≥ 0 (API) | |
| confirmed_at | timestamptz | nullable | момент подтверждения |
| note | varchar(300) | default '' | |

Ограничение: **UNIQUE `(task_id, retail_point_id)`** — одна задача поставляется в точку один раз.

### 4.10 `approvals` — очередь согласований
| Колонка | Тип | Ограничения | Примечание |
|---|---|---|---|
| id | int | PK | |
| task_id | int | FK→tasks.id (SET NULL), nullable, index | |
| from_name | varchar(120) | | от кого |
| role | varchar(80) | | роль согласующего |
| summary | varchar(300) | | что согласуется |
| type | varchar(40) | | Эскиз / КП / Счёт … |
| avatar | varchar(4) | default '' | инициалы для UI |
| color | varchar(16) | default `#5b6af0` | |
| status | enum(ApprovalStatus) | index, default `pending` | |
| comment | varchar(500) | nullable | комментарий решения (ревизия 0011) |

### 4.11 `payments` — оплаты подрядчику (1:1 к задаче)
| Колонка | Тип | Ограничения | Примечание |
|---|---|---|---|
| id | int | PK | |
| task_id | int | FK→tasks.id (CASCADE), **UNIQUE**, index | 1:1 |
| contractor | varchar(160) | | подрядчик |
| kp_date | datetime (UTC) | nullable | дата КП |
| currency | varchar(8) | default `RUB` | |
| kp_amount / sample / tirazh / prepaid / balance | varchar(80) | default '' | строковые суммы из КП (могут содержать FX) |
| status | varchar(80) | default '' | статус оплаты |

### 4.12 `documents` — файлы задач
| Колонка | Тип | Ограничения | Примечание |
|---|---|---|---|
| id | int | PK | |
| task_id | int | FK→tasks.id (CASCADE), index, **nullable** | владелец-задача (документ этапа) |
| equipment_id | int | FK→equipment.id (CASCADE), index, **nullable** | владелец-карточка (файл проекта) |
| kind | enum(DocKind) | default `other` | тип документа |
| stage | int | nullable, index | этап-вкладка (1..12), к которому привязан файл |
| filename | varchar(255) | | исходное имя (очищено) |
| storage_name | varchar(255) | | имя на диске (uuid + расширение) |
| content_type | varchar(120) | default `application/octet-stream` | |
| size | int | default 0 | байты |
| uploaded_by_id | int | FK→users.id (SET NULL), nullable | кто загрузил |

CHECK `ck_documents_owner`: `task_id IS NOT NULL OR equipment_id IS NOT NULL`
(документ принадлежит задаче ИЛИ карточке библиотеки).
Файлы хранятся в файловой системе (`UPLOAD_DIR`), в БД — только метаданные.

### task_stage_history — журнал переходов этапов

| Колонка | Тип | Ограничения | Примечание |
|---|---|---|---|
| id | int | PK | |
| task_id | int | FK→tasks.id (CASCADE), index | |
| from_stage | int | nullable | NULL = исходная запись при создании задачи |
| to_stage | int | not null | этап после перехода (1..12) |
| user_id | int | FK→users.id (SET NULL), nullable | кто инициировал переход |
| comment | varchar(300) | nullable | пояснение (напр. «авто-переход») |
| created_at | datetime (UTC) | not null | когда |

Пишется централизованно в `services/task_stage.py` (`record_creation`, `apply_transition`).

### task_stage_approvals — согласования по этапам

| Колонка | Тип | Ограничения | Примечание |
|---|---|---|---|
| id | int | PK | |
| task_id | int | FK→tasks.id (CASCADE), index | |
| stage | int | not null | этап 1..12 |
| approved | bool | default false | флаг «Согласовано» |
| user_id | int | FK→users.id (SET NULL), nullable | кто согласовал |
| comment | varchar(300) | nullable | |
| approved_at | datetime (UTC) | nullable | когда согласовано |

UNIQUE `uq_stage_approval_task_stage` (task_id, stage) — одна запись на этап.
Заменяет прежнее JSON-поле `tasks.stage_approvals` (ревизия 0007).

### nomenclature_items — номенклатура / ШК (П3)

| Колонка | Тип | Ограничения | Примечание |
|---|---|---|---|
| id | int | PK | |
| task_id | int | FK→tasks.id (CASCADE), index | |
| sku | varchar(64) | default `''` | артикул |
| barcode | varchar(64) | default `''` | штрих-код |
| name | varchar(200) | default `''` | наименование |
| qty | int | default 0 | количество |
| status | enum(NomenclatureStatus) | default `draft`, index | draft / sent_to_rc / registered |

Выгрузка: `GET /api/tasks/{code}/nomenclature.xlsx` (openpyxl). Ревизия 0010.

> **П4:** `deliveries.region` (enum `ShipmentRegion`, default `local`, index) + роль
> `shipment_manager` (ревизия 0008). **П8:** `equipment.rc_ship_date` (datetime UTC),
> `equipment.rc_remainder` (int) — отгрузка/остаток на РЦ (ревизия 0009).

### notifications — журнал напоминаний (ревизия 0012)

| Колонка | Тип | Ограничения | Примечание |
|---|---|---|---|
| id | int | PK | |
| user_id | int | FK→users.id (CASCADE), nullable, index | получатель |
| task_id | int | FK→tasks.id (CASCADE), nullable, index | |
| stage | int | nullable | этап задачи |
| rule | varchar(32) | not null | stage_stuck / deadline / approval_pending |
| message | varchar(500) | not null | текст |
| dedup_key | varchar(160) | **UNIQUE** | идемпотентность (не слать дважды) |
| status | varchar(16) | default `pending` | pending / sent / failed |
| channels | varchar(120) | default `''` | какие каналы отработали (log/email/telegram) |
| sent_at | datetime (UTC) | nullable | |

Плюс `users.telegram_chat_id` (varchar(40), nullable) — адрес для Telegram-канала.

**Движок** (`services/reminders.py`, не хранимая логика): `build_due_notifications`
сканирует открытые задачи и pending-согласования по правилам (этап завис > 4 дн,
дедлайн ≤ 3 дн, согласование висит > 2 дн), создаёт строки с дедупом по дню;
`dispatch_pending` рассылает по включённым каналам (email/telegram) или dry-run в лог.
Запуск: `python -m app.reminders` или `POST /api/internal/run-reminders` (сервис-токен).
Карта «этап → роль» получателя задаётся в сервисе.

> Этап 7 переименован в «Отгрузочные документы». В `tasks` добавлены поля
> `shipment_order_no` (varchar64), `shipment_ship_date`, `shipment_acceptance_date`
> (datetime UTC) — ревизия 0013. Документы отгрузки: `DocKind.waybill` (накладная),
> `DocKind.registry` (реестр).

---

## 5. Связи (кардинальность)

| Связь | Тип | Через |
|---|---|---|
| Group → Brand | 1 : N | `brands.group_id` |
| Brand → Task | 1 : N | `tasks.brand_id` |
| Brand → Equipment | 1 : N | `equipment.brand_id` |
| Equipment → Task | 1 : N (опц.) | `tasks.equipment_id` (nullable) |
| Task ↔ TeamMember | M : N | `task_members` |
| Task → Delivery | 1 : N | `deliveries.task_id` |
| RetailPoint → Delivery | 1 : N | `deliveries.retail_point_id` |
| Task → Approval | 1 : N | `approvals.task_id` |
| Task → Payment | 1 : 1 | `payments.task_id` (UNIQUE) |
| Task → Document | 1 : N | `documents.task_id` |
| Equipment → Document | 1 : N | `documents.equipment_id` |
| Task → StageHistory | 1 : N | `task_stage_history.task_id` |
| Task → StageApproval | 1 : N | `task_stage_approvals.task_id` (UNIQUE task+stage) |
| Task → NomenclatureItem | 1 : N | `nomenclature_items.task_id` (П3) |
| User → Document | 1 : N | `documents.uploaded_by_id` |

---

## 6. Вычисляемые значения (НЕ хранятся)

Чтобы данные не «протухали», производные значения считаются на лету:

| Значение | Как вычисляется |
|---|---|
| `days_left` задачи | `deadline_tt.date() − today_utc()` |
| `progress_pct` | `round(stage / 12 × 100)` |
| `stage_name` | `STAGES[stage − 1]` |
| ТТ-счётчики `tt_total/ok/partial/miss` | агрегаты `COUNT/SUM(CASE…)` по `deliveries`, сгруппированные по `task_id` (один запрос, без N+1) |
| KPI «ТТ без подтв.» | `SUM(deliveries WHERE status IN (partial, missing))` |
| «проблемные» точки | агрегат по `deliveries` на `retail_point_id` |

---

## 7. Принципы проектирования и масштабирование

- **Нормализация ТТ.** Доставки вынесены в отдельную таблицу `deliveries`
  (задача × точка), а не хранятся счётчиками на задаче — это даёт историю,
  статусы по каждой точке и корректные агрегаты.
- **Stateless-доступ.** Состояние только в БД; API-воркеры масштабируются
  горизонтально за балансировщиком.
- **Индексы** на всех FK и часто фильтруемых колонках (`stage`, `deadline_tt`,
  `status`, `code`, `email`, `city`).
- **Пагинация** на списках (задачи, точки) — выдача не растёт неограниченно.
- **JSON для гибких флагов.** Применяем только для коротких неизменяемых наборов.
  Согласования по этапам вынесены из JSON в таблицу `task_stage_approvals`
  (ревизия 0007), т.к. потребовались метаданные (кто/когда) — растущую логику в
  JSON не держим (см. CONTRIBUTING).
- **Деньги** — целые единицы; смешанные/валютные суммы из КП хранятся как строки
  в `payments` (исторические значения «как в КП»), расчётные — в `int`-полях задачи.

---

## 8. Миграции и версионирование

- Сейчас схема создаётся через `Base.metadata.create_all()` на старте (удобно для
  разработки на SQLite).
- **Для production** перейти на **Alembic**: каждая правка модели → ревизия миграции;
  это обеспечивает безопасные изменения без потери данных (в отличие от `create_all`,
  который не изменяет уже существующие таблицы).

---

## 9. Запланированные расширения (для будущих ревизий)

Эти сущности ещё не в схеме — фиксируем как план, чтобы заранее учесть связи:

- **Штрих-коды / номенклатура (этап 9).** Таблица `barcodes` (или `nomenclature_items`):
  `task_id`, `sku`, `barcode`, `status` (черновик/направлено на РЦ/заведено),
  ссылка на сгенерированный Excel-шаблон; плюс `documents.kind = nomenclature`.
- **Отгрузка по регионам (этап 10).** Поле `region` (`РЦ` / `СНГ` / `Middle East`)
  на `deliveries` или отдельная таблица `shipments` с координацией отдела отгрузки;
  роль `shipment_manager` в `Role`.
- **Библиотека (расширение `equipment`).** Поля: `barcode_layout`, `barcode_excel`
  (ссылки на документы), `ds_doc`, `invoice_doc`, `rc_ship_date`, `rc_remainder`.
- **Интеграция с 1С.** Импорт фактических оплат/реестра (CSV) — отдельный слой
  синхронизации; на стороне БД — поле источника/времени синхронизации в `payments`.
- **Аудит.** Журнал переходов этапов — **реализован** (`task_stage_history`, ревизия 0006).
  Расширение на оплаты/прочие изменения (`audit_log`) — план.
