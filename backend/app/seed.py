"""Idempotent seed reproducing the original dashboard mock.

Now also seeds: users (one per role), a retail-point catalog, and individual
delivery rows whose statuses sum to the original TT counts per task.
"""
from __future__ import annotations

import datetime as dt
import json

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from . import models, security
from .timeutils import to_utc_datetime

GROUPS = [
    {"code": "A", "name": "Группа A", "color": "#5b6af0", "budget_planned": 0, "budget_spent": 0},
    {"code": "B", "name": "Группа B", "color": "#06d6a0", "budget_planned": 0, "budget_spent": 0},
    {"code": "C", "name": "Группа C", "color": "#f59e0b", "budget_planned": 0, "budget_spent": 0},
]

BRANDS = [
    ("Darling", "A"), ("Noise", "A"), ("Neydo", "A"), ("Stereotype", "A"), ("Nunkoro", "A"),
    ("OKOLO", "B"), ("Nudi Branches", "B"), ("Any Buddy", "B"), ("Go Ta Pa", "B"), ("Oss To Oss", "B"), ("My Taui", "B"),
    ("RAD", "C"), ("AndPlus", "C"),
]

# tt = (total, ok, partial, miss); remaining (total-ok-partial-miss) become 'pending'
TASKS = [
    {"code": "RD-041", "brand": "Lumière", "name": "Подставка Serum Pro Display", "stage": 6, "days_left": 8, "budget": 320000, "sample": 45000, "tirazh": 275000, "prepaid": 137500, "currency": "RUB", "tt": (42, 38, 2, 2), "team": ["А.Козлова", "В.Петров", "О.Сидорова"], "urgent": True},
    {"code": "RD-038", "brand": "Botanica", "name": "Корнер Herbal Collection", "stage": 8, "days_left": 22, "budget": 980000, "sample": 120000, "tirazh": 860000, "prepaid": 430000, "currency": "RUB", "tt": (87, 87, 0, 0), "team": ["А.Козлова", "М.Иванов"], "urgent": False},
    {"code": "RD-044", "brand": "Velvet", "name": "Ёмкость Prestige Line", "stage": 3, "days_left": 61, "budget": 0, "sample": 0, "tirazh": 0, "prepaid": 0, "currency": "EUR", "tt": (0, 0, 0, 0), "team": ["А.Козлова", "В.Петров"], "urgent": False},
    {"code": "RD-039", "brand": "Novalux", "name": "Дисплей Eye Collection", "stage": 10, "days_left": 3, "budget": 540000, "sample": 60000, "tirazh": 480000, "prepaid": 480000, "currency": "RUB", "tt": (63, 44, 8, 11), "team": ["А.Козлова", "О.Сидорова", "К.Белов"], "urgent": True},
    {"code": "RD-042", "brand": "SkinLab", "name": "Полка-авторизация Peptide Rx", "stage": 4, "days_left": 45, "budget": 190000, "sample": 30000, "tirazh": 0, "prepaid": 0, "currency": "RUB", "tt": (0, 0, 0, 0), "team": ["А.Козлова", "М.Иванов"], "urgent": False},
    {"code": "RD-040", "brand": "Premiere", "name": "Корнер Gold Signature", "stage": 7, "days_left": 14, "budget": 1200000, "sample": 180000, "tirazh": 1020000, "prepaid": 510000, "currency": "USD", "tt": (28, 0, 0, 0), "team": ["А.Козлова", "В.Петров", "О.Сидорова", "К.Белов"], "urgent": True},
]

APPROVALS = [
    {"from_name": "Команда Lumière", "role": "Бренд", "code": "RD-041", "summary": "RD-041 — эскиз Serum Pro Display", "type": "Эскиз", "avatar": "ЛЮ", "color": "#5b6af0"},
    {"from_name": "И. Воронов", "role": "Директор отдела", "code": "RD-040", "summary": "RD-040 — КП подрядчика Gold Corner", "type": "КП", "avatar": "ИВ", "color": "#f59e0b"},
    {"from_name": "Ритейлер-команда", "role": "Ритейлер", "code": "RD-041", "summary": "RD-041 — размеры и материал", "type": "Эскиз", "avatar": "РТ", "color": "#06d6a0"},
    {"from_name": "Бухгалтерия", "role": "Оплата", "code": "RD-039", "summary": "RD-039 — счёт финальной оплаты", "type": "Счёт", "avatar": "БУ", "color": "#8b5cf6"},
]

PAYMENTS = [
    {"code": "RD-041", "contractor": "Plastform LLC", "kp_offset": -21, "currency": "RUB", "kp_amount": "45 000 ₽", "sample": "45 000 ₽", "tirazh": "275 000 ₽", "prepaid": "137 500 ₽", "balance": "137 500 ₽", "status": "Ожидает финала"},
    {"code": "RD-040", "contractor": "Eurostand GmbH", "kp_offset": -36, "currency": "EUR", "kp_amount": "€ 12 400 (1 085 000 ₽)", "sample": "€ 1 800 (157 500 ₽)", "tirazh": "€ 10 600 (927 500 ₽)", "prepaid": "€ 5 300 (463 750 ₽)", "balance": "€ 5 300", "status": "Предоплата внесена"},
    {"code": "RD-039", "contractor": "Рекламник ООО", "kp_offset": -90, "currency": "RUB", "kp_amount": "540 000 ₽", "sample": "60 000 ₽", "tirazh": "480 000 ₽", "prepaid": "480 000 ₽", "balance": "0 ₽", "status": "Оплачен полностью"},
]

# email, name, role, password
USERS = [
    ("admin@retail.os", "Администратор", models.Role.admin, "admin123"),
    ("manager@retail.os", "А.Козлова (Менеджер)", models.Role.manager, "manager123"),
    ("brand@retail.os", "Представитель бренда", models.Role.brand, "brand123"),
    ("retailer@retail.os", "Менеджер ритейлера", models.Role.retailer, "retailer123"),
    ("shipment@retail.os", "Отдел отгрузки", models.Role.shipment_manager, "shipment123"),
    ("viewer@retail.os", "Наблюдатель", models.Role.viewer, "viewer123"),
]

CITIES = ["Москва", "СПб", "Екатеринбург", "Новосибирск", "Казань", "Краснодар",
          "Нижний Новгород", "Самара", "Ростов-на-Дону", "Уфа", "Воронеж", "Пермь"]

# Existing equipment designs available to relaunch into production
EQUIPMENT = [
    {"brand": "Lumière", "name": "Подставка Serum Pro Display", "kind": "stand", "dimensions": "45×45×120 мм", "budget": 320000, "sample": 45000, "tirazh": 275000, "produced": 3, "description": "Акрил + металл, подсветка LED"},
    {"brand": "Lumière", "name": "Витрина Lumière Premium", "kind": "display", "dimensions": "600×400×1500 мм", "budget": 850000, "sample": 110000, "tirazh": 740000, "produced": 1, "description": "Напольная витрина с зеркалом"},
    {"brand": "Novalux", "name": "Дисплей Eye Collection", "kind": "display", "dimensions": "300×200×400 мм", "budget": 540000, "sample": 60000, "tirazh": 480000, "produced": 2, "description": "Настольный дисплей, 12 SKU"},
    {"brand": "Clarity", "name": "Полка Clarity Shelf", "kind": "shelf", "dimensions": "800×250×120 мм", "budget": 180000, "sample": 25000, "tirazh": 155000, "produced": 4, "description": "Навесная полка, лого-фрезеровка"},
    {"brand": "Botanica", "name": "Корнер Herbal Collection", "kind": "corner", "dimensions": "1200×800×2000 мм", "budget": 980000, "sample": 120000, "tirazh": 860000, "produced": 1, "description": "Угловой корнер с растительным декором"},
    {"brand": "SkinLab", "name": "Полка-авторизация Peptide Rx", "kind": "shelf", "dimensions": "700×300×400 мм", "budget": 190000, "sample": 30000, "tirazh": 160000, "produced": 2, "description": "Полка с авторизацией бренда"},
    {"brand": "VitaGlow", "name": "Тестер-стенд VitaGlow", "kind": "stand", "dimensions": "350×350×300 мм", "budget": 140000, "sample": 20000, "tirazh": 120000, "produced": 5, "description": "Стенд для тестеров, 8 позиций"},
    {"brand": "Premiere", "name": "Корнер Gold Signature", "kind": "corner", "dimensions": "1500×900×2200 мм", "currency": "USD", "budget": 1200000, "sample": 180000, "tirazh": 1020000, "produced": 0, "description": "Премиальный корнер, латунь + стекло"},
    {"brand": "Velvet", "name": "Ёмкость Prestige Line", "kind": "container", "dimensions": "200×200×250 мм", "currency": "EUR", "budget": 95000, "sample": 12000, "tirazh": 83000, "produced": 1, "description": "Презентационная ёмкость, бархат"},
    {"brand": "Orbis", "name": "Дисплей Orbis Round", "kind": "display", "dimensions": "Ø500×1600 мм", "budget": 620000, "sample": 80000, "tirazh": 540000, "produced": 0, "description": "Круглый вращающийся дисплей"},
]


def _make_retail_points(db: Session, n: int = 90) -> list[models.RetailPoint]:
    points = []
    for i in range(1, n + 1):
        city = CITIES[i % len(CITIES)]
        p = models.RetailPoint(
            code=f"TT-{i:03d}",
            name=f"Магазин «Золотое Яблоко» №{i}",
            city=city,
            address=f"{city}, ТЦ, секция {100 + i}",
        )
        points.append(p)
    db.add_all(points)
    db.flush()
    return points


def seed(db: Session) -> None:
    has_groups = db.scalar(select(func.count()).select_from(models.Group))

    # Самовосстановление справочника брендов: если группы уже есть, гарантируем
    # наличие всех стандартных брендов (досоздаём недостающие — например, если
    # их удалили вручную). Без --fresh, без дублей, не трогая остальные данные.
    if has_groups:
        gmap = {g.code: g for g in db.scalars(select(models.Group)).all()}
        existing = {b.name for b in db.scalars(select(models.Brand)).all()}
        added = False
        for name, code in BRANDS:
            if name not in existing and code in gmap:
                db.add(models.Brand(name=name, group_id=gmap[code].id))
                added = True
        if added:
            db.commit()
        return

    today = dt.date.today()

    # users
    db.add_all([
        models.User(email=e, full_name=n, role=r, hashed_password=security.hash_password(pw))
        for e, n, r, pw in USERS
    ])

    # Money is stored in kopecks; seed literals are in whole currency units → ×100.
    groups = {
        g["code"]: models.Group(
            code=g["code"], name=g["name"], color=g["color"],
            budget_planned=g["budget_planned"] * 100, budget_spent=g["budget_spent"] * 100,
        )
        for g in GROUPS
    }
    db.add_all(groups.values())
    db.flush()

    brands = {name: models.Brand(name=name, group_id=groups[code].id) for name, code in BRANDS}
    db.add_all(brands.values())
    db.flush()

    points = _make_retail_points(db)

    # Демо-данные по изделиям не создаём — заказчик заполняет вручную:
    # задачи (RD-xxx), оборудование (библиотека), доставки, согласования,
    # оплаты, документы и номенклатуру. Остаются только справочники:
    # пользователи, группы, бренды, торговые точки.
    db.commit()
