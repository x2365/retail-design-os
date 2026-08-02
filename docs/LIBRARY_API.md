# LIBRARY_API — контракт для отдельного фронтенда библиотеки

**Сценарий B:** библиотека разрабатывается как **отдельный фронтенд** поверх
существующего API RetailDesign OS. Бэкенд **не меняется**. Этот документ —
**стабильная граница (контракт)**: пока фронт работает в его рамках, он
интегрируется в основной проект без переделок бэкенда.

База: `http://localhost:8000/api` (дев). Все ответы — JSON, кодировка UTF-8.

---

## 1. Общие правила (обязательно соблюдать)

- **Аутентификация:** Bearer-токен в заголовке `Authorization: Bearer <token>`.
  Токен получают через `POST /api/auth/login`. Cookies не используются
  (CORS настроен без credentials → отдельный origin работает).
- **Деньги — в копейках.** Все суммы (`est_budget`, `est_sample`, `est_tirazh`)
  приходят и принимаются в копейках. Делите на 100 при показе, умножайте на 100
  при отправке. Валюта — в поле `currency`.
- **Роли (RBAC):** чтение — любой авторизованный; запись (create/update/delete/
  produce/upload) — только `admin`/`manager`. Иначе `403`.
- **Ошибки:** стандартные коды — `401` (нет/битый токен), `403` (нет прав),
  `404` (не найдено), `409` (конфликт, напр. удаление с зависимостями),
  `413` (файл велик), `415` (тип файла), `422` (валидация). Тело: `{"detail": "..."}`.
- **Версионирование контракта:** менять только расширяя (новые **опциональные**
  поля). Существующие поля/семантику не ломать.

---

## 2. Аутентификация

### `POST /api/auth/login`
Тело — form-urlencoded (OAuth2): `username`, `password`.
```
200 → { "access_token": "<jwt>", "token_type": "bearer" }
```
Демо: `admin@retail.os / admin123`, `manager@retail.os / manager123`,
`viewer@retail.os / viewer123`.

### `GET /api/auth/me`
```
200 → { "id", "email", "full_name", "role", "is_active" }
```

---

## 3. Карточки библиотеки (`Equipment`)

Объект **EquipmentOut**:
```json
{
  "id": 1,
  "brand": "Lumière",
  "group": "A",
  "name": "Подставка Serum Pro Display",
  "kind": "stand",
  "kind_label": "Подставка",
  "description": "",
  "dimensions": "45×45×120 мм",
  "currency": "RUB",
  "est_budget": 32000000,   // копейки
  "est_sample": 4500000,
  "est_tirazh": 27500000,
  "is_active": true,
  "times_produced": 0
}
```
`kind` ∈ `display | stand | corner | shelf | container | other`.

### `GET /api/equipment`
Query (опц.): `brand=<name>`, `active_only=true`.
```
200 → [ EquipmentOut, ... ]   // ПЛОСКИЙ список (не пагинированный)
```

### `POST /api/equipment`  *(manager)*
```json
{ "brand": "Lumière", "name": "…", "kind": "stand",
  "description": "", "dimensions": "", "currency": "RUB",
  "est_budget": 0, "est_sample": 0, "est_tirazh": 0 }   // суммы в копейках
→ 201 EquipmentOut
```
`brand` должен существовать (иначе `422`); `kind` — из белого списка (иначе `422`);
суммы `≥ 0`.

### `PATCH /api/equipment/{id}`  *(manager)*
Любое подмножество полей `EquipmentUpdate`: `name, kind, description, dimensions,
currency, est_budget, est_sample, est_tirazh, is_active`. → `200 EquipmentOut`.
Архив/из архива — это `{"is_active": false|true}`.

### `DELETE /api/equipment/{id}`  *(manager)* → `204`

### `POST /api/equipment/{id}/produce`  *(manager)*
Запуск нового проекта-задачи из карточки. По правилу 1:1 создаётся **новый ТЗ со
своей карточкой**, у исходной растёт `times_produced`.
```json
{ "name": null, "deadline": "2026-09-15", "launch": "2026-09-20", "team": [] }
→ 201 TaskOut   // см. контракт задач
```
`409`, если карточка в архиве (`is_active=false`).

---

## 4. Файлы проекта (собственное хранилище карточки)

Объект **DocumentOut**:
```json
{ "id": 5, "task": null, "equipment_id": 1, "kind": "model3d",
  "kind_label": "3D-модель", "stage": null, "filename": "project.stl",
  "content_type": "model/stl", "size": 1024, "uploaded_by": "Админ",
  "created_at": "2026-06-05T08:00:00+00:00",
  "download_url": "/api/documents/5/download" }
```
`kind` ∈ `brief | kp | sketch | model3d | photo | other`.

### `GET /api/equipment/{id}/documents`
```
200 → [ DocumentOut, ... ]   // только файлы этой карточки (equipment_id)
```

### `POST /api/equipment/{id}/documents`  *(manager)*
multipart/form-data: `file` (бинарный), `kind` (строка).
```
201 → DocumentOut
```
Ограничения: расширение из белого списка (pdf, png, jpg, jpeg, webp, gif, svg,
doc(x), xls(x), csv, ppt(x), stl, obj, step, stp, 3mf, dwg, ai, psd, eps, zip,
rar, 7z, txt) → иначе `415`; размер ≤ 25 МБ → иначе `413`; пустой файл → `422`.

### `GET /api/documents/{id}/download`  *(любой авторизованный)*
Возвращает файл (`Content-Disposition: attachment`). Используйте `fetch` с
заголовком авторизации и `blob()` (URL нельзя открыть напрямую — нужен токен).

### `DELETE /api/documents/{id}`  *(manager)* → `204`

---

## 5. Справочники (для выпадающих списков)

### `GET /api/brands` — список брендов (для поля `brand` при создании карточки).
### `GET /api/dashboard/meta` — содержит `stages` (подписи 12 этапов) и пр.

---

## 6. Как разрабатывать и запускать отдельный фронт

1. Поднять бэкенд как обычно (`uvicorn app.main:app --reload`, порт 8000).
2. Свой фронт запускать на любом порту/origin — CORS разрешает (bearer в header,
   не cookie). Базу API задать конфигом (`API_BASE = "http://localhost:8000/api"`).
3. Логин → сохранить токен в памяти → слать во всех запросах.
4. Соблюдать раздел 1 (копейки, роли, ошибки).

## 7. Как интегрировать обратно в основной проект

Любой из вариантов (бэкенд не меняется):
- **Встроить как раздел** основного фронта (отдельная вкладка/маршрут), указав тот
  же `API_BASE`.
- **iframe/мини-приложение** на отдельном маршруте.
- **Слить файлы** в основной `index.html`, если фронт сделан в той же стилистике.

Условие безболезненной интеграции: фронт **не выходит за этот контракт** и
обращается только к перечисленным эндпоинтам. Любую новую потребность (новое поле,
новый фильтр) — сначала согласовать как расширение API (опциональное, обратносов-
местимое), затем использовать. См. `CONTRIBUTING.md`.
