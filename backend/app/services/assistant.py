"""Локальный ассистент-копайлот: tool-calling поверх существующих данных.

Модель работает локально (Ollama, OpenAI-совместимый API). Данные не уходят
с машины. Ассистент только читает — никаких изменений. Если LLM выключен или
недоступен — возвращаем понятное сообщение, дашборд не затрагивается.
"""

from __future__ import annotations

import json
from collections.abc import Callable
from typing import Any

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from .. import models
from ..config import get_settings
from ..models import STAGE_LABELS, TaskStage

settings = get_settings()

# ──────────────────────────────────────────────────────────────────────────
# Инструменты (только чтение). Каждый: (json-schema для модели, обработчик).
# Обработчик получает (db, **args) и возвращает JSON-сериализуемый результат.
# ──────────────────────────────────────────────────────────────────────────


def _money(kop: int | None, currency: str = "RUB") -> str:
    sym = {"RUB": "\u20bd", "USD": "$", "EUR": "\u20ac"}.get(currency, currency)
    return f"{(kop or 0) / 100:,.0f} {sym}".replace(",", " ")


def _ru_date(d) -> str | None:
    return d.strftime("%d.%m.%y") if d else None


def _stage_label(s: int) -> str:
    try:
        return STAGE_LABELS[TaskStage(s)]
    except Exception:
        return str(s)


def _task_brief(t: models.Task) -> dict:
    return {
        "code": t.code,
        "name": t.name,
        "brand": t.brand.name if t.brand else None,
        "group": t.brand.group.code if (t.brand and t.brand.group) else None,
        "stage": t.stage,
        "stage_label": _stage_label(t.stage),
        "urgent": bool(t.urgent),
        "deadline": _ru_date(t.deadline_tt),
        "launch": _ru_date(t.launch_date),
        "budget": _money(t.budget, t.currency),
        "payment_status": t.payment_status,
    }


def tool_list_tasks(
    db: Session,
    brand: str | None = None,
    group: str | None = None,
    stage: int | None = None,
    urgent: bool | None = None,
    overdue: bool | None = None,
    limit: int = 50,
) -> dict:
    import datetime as dt

    q = select(models.Task).join(models.Brand, isouter=True)
    if brand:
        q = q.where(models.Brand.name == brand)
    if group:
        q = q.join(models.Group, isouter=True).where(models.Group.code == group)
    if stage is not None:
        q = q.where(models.Task.stage == stage)
    if urgent is not None:
        q = q.where(models.Task.urgent == urgent)
    rows = db.scalars(q.order_by(models.Task.code).limit(min(limit, 200))).all()
    today = dt.date.today()
    out = []
    for t in rows:
        if overdue:
            if not (t.deadline_tt and t.deadline_tt.date() < today and t.stage < models.LAST_STAGE):
                continue
        out.append(_task_brief(t))
    return {"count": len(out), "tasks": out}


def tool_get_task(db: Session, code: str) -> dict:
    t = db.scalar(select(models.Task).where(models.Task.code == code))
    if not t:
        return {"error": f"Задача {code} не найдена"}
    d = _task_brief(t)
    d["gates"] = {
        "prep": {"brand": bool(t.prep_brand_approved_at), "network": bool(t.prep_zya_approved_at)},
        "kp": {
            "manager": bool(t.kp_manager_approved_at),
            "director": bool(t.kp_director_approved_at),
            "network": bool(t.kp_network_approved_at),
        },
        "sample": {
            "qc": bool(t.sample_qc_approved_at),
            "brand": bool(t.sample_brand_approved_at),
            "network": bool(t.sample_network_approved_at),
        },
    }
    d["dimensions"] = t.dimensions or None
    return d


def tool_get_kpis(db: Session) -> dict:
    active = (
        db.scalar(
            select(func.count())
            .select_from(models.Task)
            .where(models.Task.stage < models.LAST_STAGE)
        )
        or 0
    )
    closed = (
        db.scalar(
            select(func.count())
            .select_from(models.Task)
            .where(models.Task.stage >= models.LAST_STAGE)
        )
        or 0
    )
    brands = db.scalar(select(func.count()).select_from(models.Brand)) or 0
    groups = db.scalar(select(func.count()).select_from(models.Group)) or 0
    return {"active_tasks": active, "closed_tasks": closed, "brands": brands, "groups": groups}


def tool_list_brands(db: Session) -> dict:
    rows = db.scalars(select(models.Brand).join(models.Group, isouter=True)).all()
    return {"brands": [{"name": b.name, "group": b.group.code if b.group else None} for b in rows]}


def tool_group_budgets(db: Session) -> dict:
    rows = db.scalars(select(models.Group).order_by(models.Group.code)).all()
    return {
        "groups": [
            {
                "code": g.code,
                "name": g.name,
                "planned": _money(g.budget_planned),
                "spent": _money(g.budget_spent),
            }
            for g in rows
        ]
    }


def tool_pending_approvals(db: Session) -> dict:
    # очередь согласований выводится из задач на этапах-гейтах
    from ..routers.approvals import _derived_approvals

    items = _derived_approvals(db)
    return {
        "count": len(items),
        "approvals": [
            {"task": a["task"], "type": a["type"], "who": a["role"], "summary": a["summary"]}
            for a in items
        ],
    }


def tool_list_deliveries(db: Session, code: str) -> dict:
    t = db.scalar(select(models.Task).where(models.Task.code == code))
    if not t:
        return {"error": f"Задача {code} не найдена"}
    rows = db.scalars(select(models.Delivery).where(models.Delivery.task_id == t.id)).all()
    ru = {"pending": "Приёмка", "delivered": "Получено", "partial": "Есть брак"}
    res = []
    for d in rows:
        p = d.retail_point
        res.append(
            {
                "point": p.name if p else None,
                "city": p.city if p else None,
                "status": ru.get(d.status.value, d.status.value),
            }
        )
    return {"count": len(res), "deliveries": res}


def tool_list_contractors(db: Session) -> dict:
    rows = db.scalars(select(models.Contractor).where(models.Contractor.is_active.is_(True))).all()
    return {"contractors": [{"name": c.name, "contact": c.contact or None} for c in rows]}


# Реестр инструментов: имя → (схема параметров, обработчик)
TOOLS: dict[str, tuple[dict, Callable]] = {
    "list_tasks": (
        {
            "type": "object",
            "properties": {
                "brand": {"type": "string", "description": "название бренда, напр. Darling"},
                "group": {"type": "string", "enum": ["A", "B", "C"]},
                "stage": {"type": "integer", "description": "этап 1..10"},
                "urgent": {"type": "boolean"},
                "overdue": {"type": "boolean", "description": "только просроченные по дедлайну"},
                "limit": {"type": "integer"},
            },
        },
        tool_list_tasks,
    ),
    "get_task": (
        {"type": "object", "properties": {"code": {"type": "string"}}, "required": ["code"]},
        tool_get_task,
    ),
    "get_kpis": ({"type": "object", "properties": {}}, tool_get_kpis),
    "list_brands": ({"type": "object", "properties": {}}, tool_list_brands),
    "group_budgets": ({"type": "object", "properties": {}}, tool_group_budgets),
    "pending_approvals": ({"type": "object", "properties": {}}, tool_pending_approvals),
    "list_deliveries": (
        {"type": "object", "properties": {"code": {"type": "string"}}, "required": ["code"]},
        tool_list_deliveries,
    ),
    "list_contractors": ({"type": "object", "properties": {}}, tool_list_contractors),
}

_TOOL_DESCRIPTIONS = {
    "list_tasks": "Список задач (изделий) с фильтрами: бренд, группа, этап, срочные, просроченные.",
    "get_task": "Детали одной задачи по коду (RD-xxx): этап, бюджет, согласования, даты, размеры.",
    "get_kpis": "Сводка дашборда: активные/закрытые задачи, число брендов и групп.",
    "list_brands": "Список брендов с группой.",
    "group_budgets": "Плановый и освоенный бюджет по группам A/B/C.",
    "pending_approvals": "Что сейчас ждёт согласования (задачи на этапах Согласования/КП/Образец).",
    "list_deliveries": "Статусы по торговым точкам для задачи (приёмка/получено/есть брак).",
    "list_contractors": "Справочник подрядчиков.",
}


def _tools_schema() -> list[dict]:
    return [
        {
            "type": "function",
            "function": {
                "name": name,
                "description": _TOOL_DESCRIPTIONS.get(name, name),
                "parameters": schema,
            },
        }
        for name, (schema, _) in TOOLS.items()
    ]


SYSTEM_PROMPT = (
    "Ты — встроенный ассистент-копайлот системы учёта производства торгового "
    "оборудования (POSM) для ритейлера «Золотое Яблоко». Отвечай по-русски, кратко "
    "и по делу. Все факты и цифры бери ТОЛЬКО через инструменты — не выдумывай. "
    "Если данных нет — так и скажи. Деньги уже отформатированы инструментами. "
    "Ты только читаешь данные и ничего не меняешь."
)


def disabled_message() -> dict:
    return {
        "disabled": True,
        "answer": "Ассистент выключен. Запустите Ollama с моделью «"
        + settings.llm_model
        + "» и включите LLM_ENABLED, чтобы пользоваться копайлотом.",
    }


def _llm_chat(messages: list[dict], tools: list[dict] | None) -> dict:
    """Один вызов локальной модели (OpenAI-совместимый chat.completions)."""
    import httpx  # ленивый импорт: нужен только при включённом ассистенте

    payload: dict[str, Any] = {
        "model": settings.llm_model,
        "messages": messages,
        "temperature": 0.2,
    }
    if tools:
        payload["tools"] = tools
    headers = {
        "Authorization": f"Bearer {settings.llm_api_key}",
        "Content-Type": "application/json",
    }
    url = settings.llm_base_url.rstrip("/") + "/chat/completions"
    with httpx.Client(timeout=settings.llm_timeout) as client:
        r = client.post(url, json=payload, headers=headers)
        r.raise_for_status()
        return r.json()


def run_assistant(
    db: Session, query: str, screen: str | None = None, filters: dict | None = None
) -> dict:
    """Главная точка: tool-calling цикл. Возвращает {answer, used_tools?}."""
    if not settings.llm_enabled:
        return disabled_message()

    try:
        import httpx
    except ImportError:
        return {
            "error": "no_httpx",
            "answer": "Для ассистента нужен пакет httpx. Установите его: pip install httpx",
        }

    ctx = ""
    if screen:
        ctx += f"\nТекущий экран пользователя: {screen}."
    if filters:
        ctx += f"\nАктивные фильтры на экране: {json.dumps(filters, ensure_ascii=False)}."

    messages: list[dict] = [
        {"role": "system", "content": SYSTEM_PROMPT + ctx},
        {"role": "user", "content": query},
    ]
    tools = _tools_schema()
    used: list[str] = []

    try:
        for _ in range(settings.llm_max_tool_rounds):
            data = _llm_chat(messages, tools)
            msg = data["choices"][0]["message"]
            tool_calls = msg.get("tool_calls") or []
            if not tool_calls:
                return {"answer": (msg.get("content") or "").strip(), "used_tools": used}
            # отдаём ассистентское сообщение с запросами инструментов обратно в историю
            messages.append(
                {"role": "assistant", "content": msg.get("content") or "", "tool_calls": tool_calls}
            )
            for call in tool_calls:
                fn = call.get("function", {})
                name = fn.get("name")
                try:
                    args = json.loads(fn.get("arguments") or "{}")
                except Exception:
                    args = {}
                entry = TOOLS.get(name)
                if not entry:
                    result = {"error": f"неизвестный инструмент {name}"}
                else:
                    used.append(name)
                    try:
                        result = entry[1](db, **args)
                    except TypeError as e:
                        result = {"error": f"неверные аргументы: {e}"}
                    except Exception as e:  # инструмент не должен ронять весь запрос
                        result = {"error": str(e)}
                messages.append(
                    {
                        "role": "tool",
                        "tool_call_id": call.get("id", name),
                        "name": name,
                        "content": json.dumps(result, ensure_ascii=False),
                    }
                )
        # израсходовали раунды — финальный ответ без инструментов
        data = _llm_chat(messages, None)
        return {
            "answer": (data["choices"][0]["message"].get("content") or "").strip(),
            "used_tools": used,
        }
    except httpx.ConnectError:
        return {
            "error": "no_connection",
            "answer": "Не удалось подключиться к локальной модели. "
            "Запущена ли Ollama (localhost:11434)?",
        }
    except httpx.HTTPStatusError as e:
        return {
            "error": "llm_http",
            "answer": f"Модель вернула ошибку: {e.response.status_code}. "
            f"Проверьте, что модель «{settings.llm_model}» загружена (ollama pull).",
        }
    except Exception as e:
        return {"error": "llm_error", "answer": f"Ошибка ассистента: {e}"}
