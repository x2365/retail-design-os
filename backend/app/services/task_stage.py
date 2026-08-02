"""Машина переходов между этапами Task (BUSINESS_RULES §2).

Правила (согласовано):
- Вперёд — только на следующий этап (current + 1). Перескок запрещён.
- Назад — на любой предыдущий этап (revert разрешён).
- Исключений из последовательности нет.
- Предусловия этапа CLOSED (все Deliveries=DELIVERED, есть Payment, все
  обязательные Approvals) проверяются в `check_close_preconditions` и
  применяются в `apply_transition` при переходе на CLOSED.

Слой services не лезет в HTTP — бросает ValueError, роутер транслирует в 4xx.
"""
from __future__ import annotations

from sqlalchemy.orm import Session

from ..models import (
    TaskStage, TaskStageHistory,
    Delivery, DeliveryStatus, Approval, ApprovalStatus, Payment,
)

FIRST = int(TaskStage.BRIEF_RECEIVED)
LAST = int(TaskStage.CLOSED)


def label(stage: int) -> str:
    from ..models import STAGE_LABELS
    return STAGE_LABELS[TaskStage(stage)]


def validate_stage_value(stage: int) -> TaskStage:
    if stage not in (s.value for s in TaskStage):
        raise ValueError(f"Недопустимый этап {stage}; допустимо {FIRST}..{LAST}")
    return TaskStage(stage)


def validate_transition(current: int, target: int) -> None:
    """Разрешает: target == current (no-op), target == current+1 (вперёд на 1),
    target < current (возврат). Запрещает: перескок вперёд > 1 этап."""
    validate_stage_value(current)
    validate_stage_value(target)
    if target == current:
        return
    if target > current and target != current + 1:
        raise ValueError(
            f"Нельзя перескочить с этапа {current} ({label(current)}) сразу на "
            f"{target} ({label(target)}). Двигайтесь последовательно (по одному)."
        )
    # target == current+1 (вперёд) или target < current (возврат) — разрешено.


def next_stage(current: int) -> int:
    """Следующий этап (для автоперехода после согласования). Не выходит за LAST."""
    return min(current + 1, LAST)


def record_transition(
    db: Session, *, task_id: int, from_stage: int | None, to_stage: int,
    user_id: int | None = None, comment: str | None = None,
) -> None:
    """Пишет одну запись в лог переходов. Коммит — на вызывающем коде."""
    db.add(TaskStageHistory(
        task_id=task_id, from_stage=from_stage, to_stage=to_stage,
        user_id=user_id, comment=comment,
    ))


def check_stage_preconditions(db: Session, task, stage: int) -> list[str]:
    """Предусловия ВЫХОДА с этапа `stage` (внутренние согласования карточки).

    Возвращает список невыполненных условий (пустой = можно двигаться дальше).
    Применяется только при движении вперёд; возврат назад не блокируется.
    Этап CLOSED проверяется отдельно в check_close_preconditions.
    """
    from sqlalchemy import func, select as _select
    from ..models import Document, DocKind
    import json as _json

    def has_doc(*kinds) -> bool:
        return bool(db.scalar(
            _select(func.count()).select_from(Document)
            .where(Document.task_id == task.id, Document.kind.in_(list(kinds)))
        ))

    reasons: list[str] = []
    s = int(stage)

    if s == 1:  # ТЗ получено → нужно заполненное ТЗ
        brief = {}
        try:
            brief = _json.loads(task.brief_data) if task.brief_data else {}
        except Exception:
            brief = {}
        if not (brief.get("product_name") or task.name):
            reasons.append("не заполнено ТЗ (укажите хотя бы название продукта)")
    elif s == 2:  # Разработка дизайна → нужен загруженный дизайн
        if not has_doc(DocKind.sketch, DocKind.model3d, DocKind.photo):
            reasons.append("не загружен файл дизайна")
    elif s == 3:  # Согласования → согласование бренда + сети
        if not task.prep_brand_approved_at:
            reasons.append("нет согласования бренда")
        if not task.prep_zya_approved_at:
            reasons.append("нет согласования сети")
    elif s == 5:  # Бюджет и КП → согласование финансы + бренд + сеть
        if not task.kp_manager_approved_at:
            reasons.append("нет согласования финансов")
        if not task.kp_director_approved_at:
            reasons.append("нет согласования бренда")
        if not task.kp_network_approved_at:
            reasons.append("нет согласования сети")
    elif s == 6:  # ДС и Счёт → загружены ДС и счёт
        if not has_doc(DocKind.ds):
            reasons.append("не загружено ДС")
        if not has_doc(DocKind.invoice):
            reasons.append("не загружен счёт")
    elif s == 7:  # Образец и Производство → образец утверждён
        if not task.sample_approved_at:
            reasons.append("образец не утверждён")
    # этапы 4 (SUMMARY), 8–11 — без жёстких внутренних гейтов на этом шаге
    return reasons


def check_close_preconditions(db: Session, task) -> list[str]:
    """Предусловия закрытия задачи (этап CLOSED) по BUSINESS_RULES:
    все поставки доставлены + есть оплата + все согласования согласованы.
    Возвращает список невыполненных условий (пустой = можно закрывать).
    """
    from sqlalchemy import func, select as _select

    reasons: list[str] = []

    not_delivered = db.scalar(
        _select(func.count())
        .select_from(Delivery)
        .where(Delivery.task_id == task.id, Delivery.status != DeliveryStatus.delivered)
    )
    if not_delivered:
        reasons.append(f"не все ТТ доставлены (не доставлено: {not_delivered})")

    has_payment = db.scalar(
        _select(func.count()).select_from(Payment).where(Payment.task_id == task.id)
    )
    if not has_payment:
        reasons.append("нет оплаты (Payment)")

    not_approved = db.scalar(
        _select(func.count())
        .select_from(Approval)
        .where(Approval.task_id == task.id, Approval.status != ApprovalStatus.approved)
    )
    if not_approved:
        reasons.append(f"есть несогласованные согласования ({not_approved})")

    return reasons


def apply_transition(
    db: Session, task, target: int, *, user_id: int | None = None, comment: str | None = None,
) -> None:
    """Валидирует переход, логирует его и выставляет task.stage.

    Бросает ValueError при недопустимом переходе (роутер транслирует в 4xx).
    Переход на CLOSED дополнительно проверяет предусловия закрытия.
    No-op, если target == текущему этапу.
    """
    validate_transition(task.stage, target)
    if target == task.stage:
        return
    # Движение вперёд — проверяем внутренние согласования покидаемого этапа.
    if target > task.stage:
        pre = check_stage_preconditions(db, task, task.stage)
        if pre:
            raise ValueError(
                f"Этап «{label(task.stage)}» не завершён: " + "; ".join(pre) + "."
            )
    if target == LAST:
        reasons = check_close_preconditions(db, task)
        if reasons:
            raise ValueError("Нельзя закрыть задачу: " + "; ".join(reasons) + ".")
    record_transition(
        db, task_id=task.id, from_stage=task.stage, to_stage=target,
        user_id=user_id, comment=comment,
    )
    task.stage = target


def record_creation(db: Session, task, *, user_id: int | None = None) -> None:
    """Исходная запись истории при создании задачи (from_stage = NULL)."""
    record_transition(
        db, task_id=task.id, from_stage=None, to_stage=task.stage,
        user_id=user_id, comment="создание задачи",
    )
