"""Библиотека проектов. Каждая задача (ТЗ) имеет ровно одну карточку (Equipment,
1:1). Карточка — «дом проекта»: на ней лежат полные файлы проекта (Document с
equipment_id), отдельно от рабочих документов по этапам задачи.
"""

from __future__ import annotations

from sqlalchemy.orm import Session

from .. import models


def ensure_library_card(db: Session, task: models.Task) -> models.Equipment:
    """Гарантирует наличие карточки библиотеки для задачи (1:1).

    Если задача уже привязана (task.equipment_id) — возвращает её карточку.
    Иначе создаёт новую карточку из полей задачи и привязывает задачу к ней.
    Коммит выполняет вызывающий код.
    """
    if task.equipment_id:
        card = db.get(models.Equipment, task.equipment_id)
        if card:
            return card
    card = models.Equipment(
        brand_id=task.brand_id,
        name=task.name,
        kind="other",
        currency=task.currency,
        est_budget=task.production_cost,
        est_sample=task.sample_cost,
        est_tirazh=task.tirazh_cost,
        is_active=True,
        times_produced=0,
    )
    db.add(card)
    db.flush()  # need card.id
    task.equipment_id = card.id
    return card
