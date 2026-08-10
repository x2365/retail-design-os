"""One-time reference-data seed: users (one per role), groups, and a
retail-point catalog. Runs only against a truly empty database (checked via
the groups table) — everything else (brands, tasks, equipment, deliveries,
payments, documents) is created by the customer through the app itself.
"""

from __future__ import annotations

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from . import models, security

GROUPS: list[dict[str, str | int]] = [
    {"code": "A", "name": "Группа A", "color": "#5b6af0", "budget_planned": 0, "budget_spent": 0},
    {"code": "B", "name": "Группа B", "color": "#06d6a0", "budget_planned": 0, "budget_spent": 0},
    {"code": "C", "name": "Группа C", "color": "#f59e0b", "budget_planned": 0, "budget_spent": 0},
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

CITIES = [
    "Москва",
    "СПб",
    "Екатеринбург",
    "Новосибирск",
    "Казань",
    "Краснодар",
    "Нижний Новгород",
    "Самара",
    "Ростов-на-Дону",
    "Уфа",
    "Воронеж",
    "Пермь",
]

def _make_retail_points(db: Session, n: int = 90) -> list[models.RetailPoint]:
    points = []
    for i in range(1, n + 1):
        city = CITIES[i % len(CITIES)]
        p = models.RetailPoint(
            code=f"TT-{i:03d}",
            name=f"Магазин №{i}",
            city=city,
            address=f"{city}, ТЦ, секция {100 + i}",
        )
        points.append(p)
    db.add_all(points)
    db.flush()
    return points


def seed(db: Session) -> None:
    has_groups = db.scalar(select(func.count()).select_from(models.Group))

    # Справочники (пользователи/группы/бренды/точки) заводятся один раз, на
    # действительно пустой базе. Раньше здесь было самовосстановление
    # стандартного списка брендов при каждом старте — убрано: оно тихо
    # возвращало вручную удалённые placeholder-бренды на каждом деплое.
    # Бренды теперь — как и задачи — заполняются вручную через UI/API.
    if has_groups:
        return

    # users
    db.add_all(
        [
            models.User(email=e, full_name=n, role=r, hashed_password=security.hash_password(pw))
            for e, n, r, pw in USERS
        ]
    )

    # Money is stored in kopecks; seed literals are in whole currency units → ×100.
    groups = {
        g["code"]: models.Group(
            code=g["code"],
            name=g["name"],
            color=g["color"],
            budget_planned=int(g["budget_planned"]) * 100,
            budget_spent=int(g["budget_spent"]) * 100,
        )
        for g in GROUPS
    }
    db.add_all(groups.values())
    db.flush()

    _make_retail_points(db)

    # Демо-данные по изделиям не создаём — заказчик заполняет вручную:
    # бренды, задачи (RD-xxx), оборудование (библиотека), доставки,
    # согласования, оплаты, документы и номенклатуру. Остаются только
    # справочники: пользователи, группы, торговые точки.
    db.commit()
